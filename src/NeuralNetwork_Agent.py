import numpy as np
from collections import deque


def relu(mat):
	return np.multiply(mat, (mat > 0))


def relu_derivative(mat):
	return (mat > 0) * 1


class NNLayer:
	# class representing a neural net layer
	def __init__(self, input_size, output_size, activation=None, lr=0.001):
		self.input_size = input_size
		self.output_size = output_size
		self.weights = np.random.uniform(low=-0.5, high=0.5, size=(input_size, output_size))
		self.stored_weights = np.copy(self.weights)
		self.activation_function = activation
		self.lr = lr
		self.m = np.zeros((input_size, output_size))
		self.v = np.zeros((input_size, output_size))
		self.beta_1 = 0.9
		self.beta_2 = 0.999
		self.time = 1
		self.adam_epsilon = 0.00000001

	# Compute the forward pass for this layer
	def forward(self, inputs, remember_for_backprop=True):
		# inputs has shape batch_size x layer_input_size

		input_with_bias = np.append(inputs, 1)
		unactivated = None

		if remember_for_backprop:
			unactivated = np.dot(input_with_bias, self.weights)
		else:
			unactivated = np.dot(input_with_bias, self.stored_weights)

		# store variables for backward pass
		output = unactivated

		if self.activation_function != None:  # assuming here the activation function is relu, this can be made more robust

			output = self.activation_function(output)

		if remember_for_backprop:
			self.backward_store_in = input_with_bias
			self.backward_store_out = np.copy(unactivated)

		return output


	def update_weights(self, gradient):
		m_temp = np.copy(self.m)
		v_temp = np.copy(self.v)

		m_temp = self.beta_1 * m_temp + (1 - self.beta_1) * gradient
		v_temp = self.beta_2 * v_temp + (1 - self.beta_2) * (gradient * gradient)

		m_vec_hat = m_temp / (1 - np.power(self.beta_1, self.time + 0.1))
		v_vec_hat = v_temp / (1 - np.power(self.beta_2, self.time + 0.1))

		self.weights -= np.divide(self.lr * m_vec_hat, np.sqrt(v_vec_hat) + self.adam_epsilon)

		self.m = np.copy(m_temp)
		self.v = np.copy(v_temp)


	def update_time(self):
		self.time += 1


	def update_stored_weights(self):
		self.stored_weights = np.copy(self.weights)


	def backward(self, gradient_from_above):

		adjusted_mul = gradient_from_above

		# this is pointwise
		if self.activation_function != None:
			adjusted_mul = np.multiply(relu_derivative(self.backward_store_out), gradient_from_above)

		D_i = np.dot(np.transpose(np.reshape(self.backward_store_in, (1, len(self.backward_store_in)))), np.reshape(adjusted_mul, (1, len(adjusted_mul))))
		delta_i = np.dot(adjusted_mul, np.transpose(self.weights))[:-1]
		self.update_weights(D_i)

		return delta_i


class RLAgent:
	# class representing a reinforcement learning agent

	def __init__(self, params=None):
		self.agentType = "NeuralNetwork"

		if params is None:
			params = [18, 2, 64, 9, 0.95, 0.997, 0.01]

		self.input_size, \
		self.num_hidden, \
		self.hidden_size, \
		self.output_size, \
		self.gamma, \
		self.epsilon_decay, \
		self.epsilon_min = params


		self.memory = deque([], 1000000)
		self.epsilon = 1.0


		self.layers = [NNLayer(self.input_size + 1, self.hidden_size, activation=relu)]

		for i in range(self.num_hidden - 1):
			self.layers.append(NNLayer(self.hidden_size + 1, self.hidden_size, activation=relu))

		self.layers.append(NNLayer(self.hidden_size + 1, self.output_size))


	def move(self, env, piece):

		observation = env.get_array()

		values = self.forward(np.asmatrix(observation))

		squareLegalities = env.getLegalSquares()
		values = np.multiply(values, squareLegalities)

		if (np.random.random() > self.epsilon):
			index = np.argmax(values)
		else:
			index = np.random.randint(self.output_size)

		return 0b1 << index


	def forward(self, observation, remember_for_backprop=True):

		vals = np.copy(observation)
		index = 0

		for layer in self.layers:
			vals = layer.forward(vals, remember_for_backprop)
			index = index + 1

		return vals


	def remember(self, done, action, observation, prev_obs):
		self.memory.append([done, action, observation, prev_obs])


	def experience_replay(self, batch_size=20):

		if (len(self.memory) < batch_size):
			return
		else:
			batch_indices = np.random.choice(len(self.memory), batch_size)

			for index in batch_indices:

				done, action_selected, new_obs, prev_obs = self.memory[index]
				action_values = self.forward(prev_obs, remember_for_backprop=True)
				next_action_values = self.forward(new_obs, remember_for_backprop=False)
				experimental_values = np.copy(action_values)

				if done:
					experimental_values[action_selected] = -1
				else:
					experimental_values[action_selected] = 1 + self.gamma * np.max(next_action_values)

				self.backward(action_values, experimental_values)

		self.epsilon = self.epsilon if self.epsilon < self.epsilon_min else self.epsilon * self.epsilon_decay

		for layer in self.layers:
			layer.update_time()
			layer.update_stored_weights()

	def backward(self, calculated_values, experimental_values):

		# values are batched = batch_size x output_size
		delta = (calculated_values - experimental_values)

		# print('delta = {}'.format(delta))
		for layer in reversed(self.layers):
			delta = layer.backward(delta)