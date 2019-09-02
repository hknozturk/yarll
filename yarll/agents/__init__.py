from yarll.agents.registration import register_agent, make_agent

register_agent(name="A2C",
               entry_point="yarll.agents.actorcritic.a2c:A2CDiscrete",
               state_dimensions="continuous",
               action_space="discrete"
              )
register_agent(name="A2C",
               entry_point="yarll.agents.actorcritic.a2c:A2CDiscreteCNN",
               state_dimensions="multi",
               action_space="discrete"
              )
register_agent(name="A2C",
               entry_point="yarll.agents.actorcritic.a2c:A2CDiscreteCNNRNN",
               state_dimensions="multi",
               action_space="discrete",
               RNN=True
              )
register_agent(name="A2C",
               entry_point="yarll.agents.actorcritic.a2c:A2CContinuous",
               state_dimensions="continuous",
               action_space="continuous"
              )
register_agent(name="A3C",
               entry_point="yarll.agents.actorcritic.a3c:A3CDiscrete",
               state_dimensions="continuous",
               action_space="discrete"
              )
register_agent(name="A3C",
               entry_point="yarll.agents.actorcritic.a3c:A3CDiscreteCNN",
               state_dimensions="multi",
               action_space="discrete"
              )
register_agent(name="A3C",
               entry_point="yarll.agents.actorcritic.a3c:A3CDiscreteCNNRNN",
               state_dimensions="multi",
               action_space="discrete",
               RNN=True
              )
register_agent(name="A3C",
               entry_point="yarll.agents.actorcritic.a3c:A3CContinuous",
               state_dimensions="continuous",
               action_space="continuous"
              )
register_agent(name="AsyncKnowledgeTransfer",
               entry_point="yarll.agents.knowledgetransfer.async_knowledge_transfer:AsyncKnowledgeTransfer",
               state_dimensions="continuous",
               action_space="discrete"
              )
register_agent(name="PPO",
               entry_point="yarll.agents.ppo.ppo:PPODiscrete",
               state_dimensions="continuous",
               action_space="discrete"
              )
register_agent(name="PPO",
               entry_point="yarll.agents.ppo.ppo:PPOBernoulli",
               state_dimensions="continuous",
               action_space="multibinary"
               )
register_agent(name="PPO",
               entry_point="yarll.agents.ppo.ppo:PPODiscreteCNN",
               state_dimensions="multi",
               action_space="discrete"
              )
register_agent(name="PPO",
               entry_point="yarll.agents.ppo.ppo:PPOContinuous",
               state_dimensions="continuous",
               action_space="continuous"
              )
register_agent(name="PPO",
               entry_point="yarll.agents.ppo.ppo:PPOMultiDiscrete",
               state_dimensions="continuous",
               action_space="multidiscrete"
               )
register_agent(name="DPPO",
               entry_point="yarll.agents.ppo.dppo:DPPODiscrete",
               state_dimensions="continuous",
               action_space="discrete"
              )
register_agent(name="DPPO",
               entry_point="yarll.agents.ppo.dppo:DPPODiscreteCNN",
               state_dimensions="multi",
               action_space="discrete"
              )
register_agent(name="DPPO",
               entry_point="yarll.agents.ppo.dppo:DPPOContinuous",
               state_dimensions="continuous",
               action_space="continuous"
              )
register_agent(name="TRPO",
               entry_point="yarll.agents.trpo.trpo:TRPODiscrete",
               state_dimensions="continuous",
               action_space="discrete"
              )
register_agent(name="TRPO",
               entry_point="yarll.agents.trpo.trpo:TRPODiscreteCNN",
               state_dimensions="multi",
               action_space="discrete"
              )
register_agent(name="TRPO",
               entry_point="yarll.agents.trpo.trpo:TRPOContinuous",
               state_dimensions="continuous",
               action_space="continuous"
              )
register_agent(name="DTRPO",
               entry_point="yarll.agents.trpo.dtrpo:DTRPODiscrete",
               state_dimensions="continuous",
               action_space="discrete"
              )
register_agent(name="DTRPO",
               entry_point="yarll.agents.trpo.dtrpo:DTRPODiscreteCNN",
               state_dimensions="multi",
               action_space="discrete"
              )
register_agent(name="DTRPO",
               entry_point="yarll.agents.trpo.dtrpo:DTRPOContinuous",
               state_dimensions="continuous",
               action_space="continuous"
              )
register_agent(name="DDPG",
               entry_point="yarll.agents.ddpg:DDPG",
               state_dimensions="continuous",
               action_space="continuous"
              )
register_agent(name="CEM",
               entry_point="yarll.agents.cem:CEM",
               state_dimensions="continuous",
               action_space="discrete"
              )
register_agent(name="CEM",
               entry_point="yarll.agents.cem:CEM",
               state_dimensions="continuous",
               action_space="multibinary"
               )
register_agent(name="CEM",
               entry_point="yarll.agents.cem:CEM",
               state_dimensions="continuous",
               action_space="continuous"
              )
register_agent(name="Karpathy",
               entry_point="yarll.agents.karpathy:Karpathy",
               state_dimensions="continuous",
               action_space="discrete"
              )
register_agent(name="KnowledgeTransfer",
               entry_point="yarll.agents.knowledge_transfer:KnowledgeTransfer",
               state_dimensions="continuous",
               action_space="discrete"
              )
register_agent(name="REINFORCE",
               entry_point="yarll.agents.reinforce:REINFORCEDiscrete",
               state_dimensions="continuous",
               action_space="discrete"
              )
register_agent(name="REINFORCE",
               entry_point="yarll.agents.reinforce:REINFORCEDiscreteRNN",
               state_dimensions="continuous",
               action_space="discrete",
               RNN=True
              )
register_agent(name="REINFORCE",
               entry_point="yarll.agents.reinforce:REINFORCEBernoulli",
               state_dimensions="continuous",
               action_space="multibinary"
               )
register_agent(name="REINFORCE",
               entry_point="yarll.agents.reinforce:REINFORCEDiscreteCNN",
               state_dimensions="multi",
               action_space="discrete"
              )
register_agent(name="REINFORCE",
               entry_point="yarll.agents.reinforce:REINFORCEDiscreteCNNRNN",
               state_dimensions="multi",
               action_space="discrete",
               RNN=True
              )
register_agent(name="REINFORCE",
               entry_point="yarll.agents.reinforce:REINFORCEContinuous",
               state_dimensions="continuous",
               action_space="continuous"
              )
register_agent(name="REINFORCE",
               entry_point="yarll.agents.reinforce:REINFORCEContinuous",
               state_dimensions="continuous",
               action_space="continuous",
               RNN=True
               )
register_agent(name="SarsaFA",
               entry_point="yarll.agents.sarsa.sarsa_fa:SarsaFA",
               state_dimensions="continuous",
               action_space="discrete"
              )
register_agent(name="SAC",
               entry_point="yarll.agents.sac:SAC",
               state_dimensions="continuous",
               action_space="continuous"
               )
register_agent(name="QLearning",
               entry_point="yarll.agents.q_learning:QLearning",
               state_dimensions="discrete",
               action_space="discrete")
register_agent(name="FittedQIteration",
               entry_point="yarll.agents.fitted_q:FittedQIteration",
               state_dimensions="continuous",
               action_space="discrete"
               )
