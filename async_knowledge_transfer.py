#!/usr/bin/env python
# -*- coding: utf8 -*-

import sys
import os
import numpy as np
import tensorflow as tf
import logging
import argparse
from threading import Thread
import signal

from gym.spaces import Discrete

from Learner import Learner
from utils import discount_rewards, save_config
from CartPole import make_predef_CartPole_envs, make_random_CartPole_envs
from Reporter import Reporter
from gradient_ops import create_accumulative_gradients_op, add_accumulative_gradients_op, reset_accumulative_gradients_op
from knowledge_transfer import TaskLearner

class AKTThread(Thread):
    """Asynchronous knowledge transfer learner thread. Used to learn using one specific variation of a task."""
    def __init__(self, master, env, thread_id):
        super(AKTThread, self).__init__()
        self.master = master
        self.thread_id = thread_id
        self.add_accum_grad = None  # To be filled in later

        self.build_networks()
        self.states = self.master.states
        self.session = self.master.session
        self.task_learner = TaskLearner(env, self.action, self, **self.master.config)

        # Write the summary of each thread in a different directory
        self.writer = tf.summary.FileWriter(os.path.join(self.master.monitor_dir, "thread", str(self.thread_id)), self.master.session.graph)

    def build_networks(self):
        self.sparse_representation = tf.Variable(tf.random_normal([self.master.config["n_sparse_units"], self.master.nA]))
        self.probs = tf.nn.softmax(tf.matmul(self.master.L1, tf.matmul(self.master.knowledge_base, self.sparse_representation)))

        self.action = tf.squeeze(tf.multinomial(tf.log(self.probs), 1), name="action")

        good_probabilities = tf.reduce_sum(tf.multiply(self.probs, tf.one_hot(tf.cast(self.master.action_taken, tf.int32), self.master.nA)), reduction_indices=[1])
        eligibility = tf.log(good_probabilities) * self.master.advantage
        self.loss = -tf.reduce_sum(eligibility)

    def choose_action(self, state):
        """Choose an action."""
        return self.master.session.run([self.action], feed_dict={self.master.states: [state]})[0]

    def run(self):
        """Run the appropriate learning algorithm."""
        self.learn_REINFORCE() if self.master.learning_method == "REINFORCE" else self.learn_Karpathy()

    def learn_REINFORCE(self):
        """Learn using updates like in the REINFORCE algorithm."""
        reporter = Reporter()
        config = self.master.config
        total_n_trajectories = 0
        iteration = 0
        while iteration < config["n_iter"] and not self.master.stop_requested:
            iteration += 1
            self.master.session.run([self.master.reset_accum_grads])
            # Collect trajectories until we get timesteps_per_batch total timesteps
            trajectories = self.task_learner.get_trajectories()
            total_n_trajectories += len(trajectories)
            all_state = np.concatenate([trajectory["state"] for trajectory in trajectories])
            # Compute discounted sums of rewards
            rets = [discount_rewards(trajectory["reward"], config["gamma"]) for trajectory in trajectories]
            max_len = max(len(ret) for ret in rets)
            padded_rets = [np.concatenate([ret, np.zeros(max_len - len(ret))]) for ret in rets]
            # Compute time-dependent baseline
            baseline = np.mean(padded_rets, axis=0)
            # Compute advantage function
            advs = [ret - baseline[:len(ret)] for ret in rets]
            all_action = np.concatenate([trajectory["action"] for trajectory in trajectories])
            all_adv = np.concatenate(advs)
            # Do policy gradient update step
            episode_rewards = np.array([trajectory["reward"].sum() for trajectory in trajectories])  # episode total rewards
            episode_lengths = np.array([len(trajectory["reward"]) for trajectory in trajectories])  # episode lengths
            results = self.master.session.run([self.loss, self.add_accum_grad], feed_dict={
                self.master.states: all_state,
                self.master.action_taken: all_action,
                self.master.advantage: all_adv
            })
            print("Task:", self.thread_id)
            reporter.print_iteration_stats(iteration, episode_rewards, episode_lengths, total_n_trajectories)
            results = self.master.session.run([self.master.summary_op], feed_dict={
                self.master.loss: results[0],
                self.master.reward: np.mean(episode_rewards),
                self.master.episode_length: np.mean(episode_lengths)
            })
            self.writer.add_summary(results[0], iteration)
            self.writer.flush()
            self.master.session.run([self.master.apply_gradients])

    def learn_Karpathy(self):
        """Learn using updates like in the Karpathy algorithm."""
        config = self.master.config
        self.master.session.run([self.master.reset_accum_grads])

        iteration = 0
        while not self.master.stop_requested:  # Keep executing episodes until the master requests a stop (e.g. using SIGINT)
            iteration += 1
            trajectory = self.task_learner.get_trajectory()
            reward = sum(trajectory["reward"])
            action_taken = trajectory["action"]

            discounted_episode_rewards = discount_rewards(trajectory["reward"], config["gamma"])
            # standardize
            discounted_episode_rewards -= np.mean(discounted_episode_rewards)
            std = np.std(discounted_episode_rewards)
            std = std if std > 0 else 1
            discounted_episode_rewards /= std
            feedback = discounted_episode_rewards

            results = self.master.session.run([self.loss, self.add_accum_grad], feed_dict={
                self.master.states: trajectory["state"],
                self.master.action_taken: action_taken,
                self.master.advantage: feedback
            })
            results = self.master.session.run([self.master.summary_op], feed_dict={
                self.master.loss: results[0],
                self.master.reward: reward,
                self.master.episode_length: trajectory["steps"]
            })
            self.writer.add_summary(results[0], iteration)
            self.writer.flush()

            self.master.session.run([self.master.apply_gradients])
            self.master.session.run([self.master.reset_accum_grads])


class AsyncKnowledgeTransferLearner(Learner):
    """Asynchronous learner for variations of a task."""
    def __init__(self, envs, learning_method, monitor_dir, **usercfg):
        super(AsyncKnowledgeTransferLearner, self).__init__(envs[0], **usercfg)
        self.envs = envs
        self.learning_method = learning_method
        self.monitor_dir = monitor_dir
        self.nA = envs[0].action_space.n
        self.config.update(dict(
            timesteps_per_batch=2000,
            trajectories_per_batch=10,
            batch_update="timesteps",
            n_iter=400,
            gamma=0.99,
            learning_rate=0.005,
            n_hidden_units=20,
            repeat_n_actions=1,
            n_task_variations=3,
            n_sparse_units=10,
        ))
        self.config.update(usercfg)

        self.stop_requested = False

        self.session = tf.Session(config=tf.ConfigProto(
            log_device_placement=False,
            allow_soft_placement=True))

        self.build_networks()

        self.loss = tf.placeholder("float", name="loss")
        loss_summary = tf.summary.scalar("Loss", self.loss)
        self.reward = tf.placeholder("float", name="reward")
        reward_summary = tf.summary.scalar("Reward", self.reward)
        self.episode_length = tf.placeholder("float", name="episode_length")
        episode_length_summary = tf.summary.scalar("Episode_length", self.episode_length)
        self.summary_op = tf.summary.merge([loss_summary, reward_summary, episode_length_summary])

        self.jobs = [self.make_thread(env, i) for i, env in enumerate(self.envs)]

        net_vars = self.shared_vars + [job.sparse_representation for job in self.jobs]
        self.accum_grads = create_accumulative_gradients_op(net_vars, 1)
        for job in self.jobs:
            job.add_accum_grad = add_accumulative_gradients_op(
                self.shared_vars + [job.sparse_representation],
                self.accum_grads,
                job.loss,
                job.thread_id)
        self.apply_gradients = self.optimizer.apply_gradients(zip(self.accum_grads, net_vars))
        self.reset_accum_grads = reset_accumulative_gradients_op(net_vars, self.accum_grads, 1)

        self.session.run(tf.global_variables_initializer())

        if self.config["save_model"]:
            for job in self.jobs:
                tf.add_to_collection("action", job.action)
            tf.add_to_collection("states", self.states)
            self.saver = tf.train.Saver()

    def build_networks(self):
        self.states = tf.placeholder(tf.float32, name="states")
        self.action_taken = tf.placeholder(tf.float32, name="action_taken")
        self.advantage = tf.placeholder(tf.float32, name="advantage")

        W0 = tf.Variable(tf.random_normal([self.nO, self.config["n_hidden_units"]]) / np.sqrt(self.nO), name='W0')
        b0 = tf.Variable(tf.zeros([self.config["n_hidden_units"]]), name='b0')
        self.L1 = tf.tanh(tf.matmul(self.states, W0) + b0[None, :])

        self.knowledge_base = tf.Variable(tf.random_normal([self.config["n_hidden_units"], self.config["n_sparse_units"]]))

        self.shared_vars = [W0, b0, self.knowledge_base]

        self.optimizer = tf.train.RMSPropOptimizer(learning_rate=self.config["learning_rate"], decay=0.9, epsilon=1e-9)

    def signal_handler(self, signal, frame):
        """When a (SIGINT) signal is received, request the threads (via the master) to stop after completing an iteration."""
        logging.info("SIGINT signal received: Requesting a stop...")
        self.stop_requested = True

    def learn(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        for job in self.jobs:
            job.start()
        for job in self.jobs:
            job.join()

        if self.config["save_model"]:
            self.saver.save(self.session, os.path.join(self.monitor_dir, "model"))

    def make_thread(self, env, thread_id):
        return AKTThread(self, env, thread_id)

parser = argparse.ArgumentParser()
parser.add_argument("environment", metavar="env", type=str, help="Gym environment to execute the experiment on.")
parser.add_argument("monitor_path", metavar="monitor_path", type=str, help="Path where Gym monitor files may be saved")
parser.add_argument("--learning_method", metavar="learning_method", type=str, default="REINFORCE", choices=["REINFORCE", "Karpathy"])
parser.add_argument("--save_model", action="store_true", default=False, help="Save resulting model.")
parser.add_argument("--random_envs", type=int, help="Number of environments with random parameters to generate.")

def main():
    try:
        args = parser.parse_args()
    except:
        sys.exit()
    if not os.path.exists(args.monitor_path):
        os.makedirs(args.monitor_path)
    if args.environment != "CartPole-v0":
        raise NotImplementedError("Only the environment \"CartPole-v0\" is supported right now.")
    envs = make_random_CartPole_envs(args.random_envs) if args.random_envs else make_predef_CartPole_envs()
    if isinstance(envs[0].action_space, Discrete):
        agent = AsyncKnowledgeTransferLearner(envs, args.learning_method, args.monitor_path, save_model=args.save_model)
    else:
        raise NotImplementedError("Only environments with a discrete action space are supported right now.")
    save_config(args.monitor_path, agent.config, envs)
    try:
        agent.learn()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
