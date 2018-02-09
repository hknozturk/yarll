# -*- coding: utf8 -*-

import os
import tensorflow as tf
import numpy as np
from gym import wrappers

from agents.agent import Agent
from agents.actor_critic import ActorCriticNetworkDiscrete, ActorCriticNetworkDiscreteCNN, ActorCriticNetworkContinuous
from misc.utils import discount_rewards
from agents.env_runner import EnvRunner

def cso_loss(old_network, new_network, epsilon, advantage):
    ratio = tf.exp(new_network.action_log_prob - old_network.action_log_prob)
    ratio_clipped = tf.clip_by_value(ratio, 1.0 - epsilon, 1.0 + epsilon)
    return tf.minimum(ratio * advantage, ratio_clipped * advantage)

class PPO(Agent):
    """Proximal Policy Optimization agent."""
    RNN = False

    def __init__(self, env, monitor_path, video=False, **usercfg):
        super(PPO, self).__init__(**usercfg)
        self.monitor_path = monitor_path
        self.env = wrappers.Monitor(
            env,
            monitor_path,
            force=True,
            video_callable=(None if video else False))

        self.config.update(dict(
            n_hidden=20,
            gamma=0.99,
            learning_rate=0.001,
            n_iter=10000,
            batch_size=64,  # Timesteps per training batch
            n_local_steps=256,
            gradient_clip_value=0.5,
            entropy_coef=0.01,
            cso_epsilon=0.2  # Clipped surrogate objective epsilon
        ))

        with tf.variable_scope("old_network"):
            self.old_network = self.build_networks()
            self.old_network_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, tf.get_variable_scope().name)

        with tf.variable_scope("new_network"):
            self.new_network = self.build_networks()
            if self.RNN:
                self.initial_features = self.new_network.state_init
            else:
                self.initial_features = None
            self.new_network_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, tf.get_variable_scope().name)
        self.action = self.new_network.action
        self.value = self.new_network.value
        self.states = self.new_network.states
        self.r = self.new_network.r
        self.adv = self.new_network.adv
        self.actions_taken = self.new_network.actions_taken

        self.set_old_to_new = tf.group(*[v1.assign(v2) for v1, v2 in zip(self.old_network_vars, self.new_network_vars)])

        # Reduces by taking the mean instead of summing
        self.actor_loss = -tf.reduce_mean(cso_loss(self.old_network, self.new_network, self.config["cso_epsilon"], self.adv))
        self.critic_loss = tf.reduce_mean(tf.square(self.value - self.r))
        self.loss = self.actor_loss + 0.5 * self.critic_loss - self.config["entropy_coef"] * tf.reduce_mean(self.new_network.entropy)

        self.optimizer = tf.train.AdamOptimizer(self.config["learning_rate"], name="optim")
        grads = tf.gradients(self.loss, self.new_network_vars)
        grads, _ = tf.clip_by_global_norm(grads, self.config["gradient_clip_value"])

        apply_grads = self.optimizer.apply_gradients(zip(grads, self.new_network_vars))

        self._global_step = tf.get_variable(
            "global_step",
            [],
            tf.int32,
            initializer=tf.constant_initializer(0, dtype=tf.int32),
            trainable=False)

        self.n_steps = tf.shape(self.states)[0]
        inc_step = self._global_step.assign_add(self.n_steps)
        self.train_op = tf.group(apply_grads, inc_step)

        init = tf.global_variables_initializer()
        # Launch the graph.
        self.session = tf.Session()
        self.session.run(init)
        if self.config["save_model"]:
            tf.add_to_collection("action", self.action)
            tf.add_to_collection("states", self.states)
            self.saver = tf.train.Saver()
        n_steps = tf.to_float(self.n_steps)
        summary_actor_loss = tf.summary.scalar("model/Actor_loss", self.actor_loss / n_steps)
        summary_critic_loss = tf.summary.scalar("model/Critic_loss", self.critic_loss / n_steps)
        summary_loss = tf.summary.scalar("model/Loss", self.loss / n_steps)
        self.loss_summary_op = tf.summary.merge(
            [summary_actor_loss, summary_critic_loss, summary_loss])
        self.writer = tf.summary.FileWriter(os.path.join(self.monitor_path, "summaries"), self.session.graph)
        self.env_runner = EnvRunner(self.env, self, usercfg, summary_writer=self.writer)
        return

    @property
    def global_step(self):
        return self._global_step.eval(session=self.session)

    def get_critic_value(self, state, *rest):
        return self.session.run([self.value], feed_dict={self.states: state})[0].flatten()

    def choose_action(self, state, *rest):
        action, value = self.session.run([self.action, self.value], feed_dict={self.states: [state]})
        return action, value[0], []

    def get_env_action(self, action):
        return np.argmax(action)

    def get_processed_trajectories(self):
        trajectory = self.env_runner.get_steps(self.config["n_local_steps"], stop_at_trajectory_end=False)
        v = 0 if trajectory.terminal else self.get_critic_value(np.asarray(trajectory.states)[None, -1], trajectory.features[-1])
        rewards_plus_v = np.asarray(trajectory.rewards + [v])
        vpred_t = np.asarray(trajectory.values + [v])
        delta_t = trajectory.rewards + self.config["gamma"] * vpred_t[1:] - vpred_t[:-1]
        batch_r = discount_rewards(rewards_plus_v, self.config["gamma"])[:-1]
        batch_adv = discount_rewards(delta_t, self.config["gamma"])
        return trajectory.states, trajectory.actions, np.vstack(batch_adv).flatten().tolist(), batch_r, trajectory.features

    def learn(self):
        """Run learning algorithm"""
        config = self.config
        n_updates = 0
        for iteration in range(config["n_iter"]):
            # Collect trajectories until we get timesteps_per_batch total timesteps
            states, actions, advs, rs, features = self.get_processed_trajectories()
            self.session.run(self.set_old_to_new)

            indices = np.arange(len(states))
            np.random.shuffle(indices)

            batch_size = self.config["batch_size"]
            for i in range(0, len(states), batch_size):
                batch_states = np.array(states)[i:(i + batch_size)]
                batch_actions = np.array(actions)[i:(i + batch_size)]
                batch_advs = np.array(advs)[i:(i + batch_size)]
                batch_rs = np.array(rs)[i:(i + batch_size)]
                fetches = [self.loss_summary_op, self.train_op]
                feed_dict = {
                    self.states: batch_states,
                    self.old_network.states: batch_states,
                    self.actions_taken: batch_actions,
                    self.old_network.actions_taken: batch_actions,
                    self.adv: batch_advs,
                    self.r: batch_rs
                }
                summary, _ = self.session.run(fetches, feed_dict)
                self.writer.add_summary(summary, n_updates)
                n_updates += 1
                self.writer.flush()

        if self.config["save_model"]:
            tf.add_to_collection("action", self.action)
            tf.add_to_collection("states", self.states)
            self.saver.save(self.session, os.path.join(self.monitor_path, "model"))

class PPODiscrete(PPO):
    def build_networks(self):
        return ActorCriticNetworkDiscrete(
            list(self.env.observation_space.shape),
            self.env.action_space.n,
            self.config["n_hidden"])

class PPODiscreteCNN(PPODiscrete):
    def build_networks(self):
        return ActorCriticNetworkDiscreteCNN(
            list(self.env.observation_space.shape),
            self.env.action_space.n,
            self.config["n_hidden"])

class PPOContinuous(PPO):
    def build_networks(self):
        return ActorCriticNetworkContinuous(
            list(self.env.observation_space.shape),
            self.env.action_space,
            self.config["n_hidden"])

    def get_env_action(self, action):
        return action
