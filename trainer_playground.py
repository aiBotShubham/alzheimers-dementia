import glob, os, math, time
import numpy as np
np.random.seed(0)
from pathlib import Path

import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras.models import Model
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

import dataset

def train_n_folds(model_type, x, y, n_folds=5, model_dir='default'):

	train_accuracies = []
	val_accuracies = []
	fold = 0

	for train_index, val_index in KFold(n_folds).split(x):
		fold+=1

		x_train, x_val = x[train_index], x[val_index]
		y_train, y_val = y[train_index], y[val_index]
		# filenames_train, filenames_val = filenames[train_index], filenames[val_index]

		results = train_a_fold(model_type, x_train, y_train, x_val, y_val, fold, model_dir)
		train_accuracy, val_accuracy= results

		train_accuracies.append(train_accuracy)
		val_accuracies.append(val_accuracy)
	
	return train_accuracies, val_accuracies

def train_a_fold(model_type, x_train, y_train, x_val, y_val, fold, model_dir):

	print('Training fold {} of {}'.format(fold, model_type))

	if model_type == 'spectogram':
		spectogram_size = (480, 640, 3)
		model = create_spectogram_model(spectogram_size)
		epochs = 32
		batch_size = 8
		epsilon = 0.1

	elif model_type == 'pause':
		n_features = 11
		model = create_pause_model(n_features)
		epochs = 600
		batch_size = 8
		epsilon = 1e-07

	elif model_type == 'intervention':
		longest_speaker_length = 24
		model = create_intervention_model(longest_speaker_length)
		epochs = 300
		batch_size = 8
		epsilon = 1e-07

	elif model_type == 'compare':
		features_size = 24
		model = create_compare_model(features_size)
		epochs = 400
		batch_size = 8
		epsilon = 1e-07

		sc = StandardScaler()
		sc.fit(x_train)

		x_train = sc.transform(x_train)
		x_val = sc.transform(x_val)

		pca = PCA(n_components=features_size)
		pca.fit(x_train)

		x_train = pca.transform(x_train)
		x_val = pca.transform(x_val)

	checkpointer = tf.keras.callbacks.ModelCheckpoint(
			os.path.join(model_dir, model_type, 'fold_{}.h5'.format(fold)), monitor='val_loss', verbose=0, save_best_only=True,
			save_weights_only=False, mode='auto', save_freq='epoch')

	model.compile(loss=tf.keras.losses.categorical_crossentropy,
				  optimizer=tf.keras.optimizers.Adam(lr=0.01, epsilon=epsilon),
				  metrics=['categorical_accuracy'])
	model.fit(x_train, y_train,
			  batch_size=batch_size,
			  epochs=epochs,
			  verbose=1,
			  callbacks=[checkpointer],
			  validation_data=(x_val, y_val))

	model = tf.keras.models.load_model(os.path.join(model_dir, model_type, 'fold_{}.h5'.format(fold)))

	train_score = model.evaluate(x_train, y_train, verbose=0)
	train_accuracy = train_score[1]
	train_loss = train_score[0]

	val_score = model.evaluate(x_val, y_val, verbose=0)
	print('Fold Val accuracy:', val_score[1])
	val_accuracy = val_score[1]
	val_loss = val_score[0]

	return train_accuracy, val_accuracy

def create_intervention_model(longest_speaker_length):
	model = tf.keras.Sequential()
	model.add(layers.LSTM(16, input_shape=(longest_speaker_length, 3)))
	model.add(layers.BatchNormalization())
	# model.add(layers.Dropout(0.2))
	model.add(layers.Dense(16, activation='relu'))
	model.add(layers.BatchNormalization())
	# model.add(layers.Dropout(0.2))
	model.add(layers.Dense(2, activation='softmax'))
	return model

def create_spectogram_model(spectogram_size):
	model2_input = layers.Input(shape=spectogram_size,  name='spectrogram_input')
	model2_BN = layers.BatchNormalization()(model2_input)
	
	model2_hidden1 = layers.Conv2D(16, kernel_size=(3, 3), strides=(1, 1),
						 activation='relu')(model2_BN)
	# model2_hidden2 = layers.Conv2D(16, kernel_size=(3, 3), strides=(2, 2),
	# 					 activation='relu')(model2_hidden1)
	model2_BN1 = layers.BatchNormalization()(model2_hidden1)
	model2_hidden2 = layers.MaxPool2D()(model2_BN1)
	
	model2_hidden3 = layers.Conv2D(32, kernel_size=(3, 3), strides=(1, 1),
						 activation='relu')(model2_hidden2)
	# model2_hidden4 = layers.Conv2D(32, kernel_size=(3, 3), strides=(2, 2),
	# 					 activation='relu')(model2_hidden3)
	model2_BN2 = layers.BatchNormalization()(model2_hidden3)
	model2_hidden4 = layers.MaxPool2D()(model2_BN2)

	model2_hidden5 = layers.Conv2D(64, kernel_size=(5, 5), strides=(1, 1),
						 activation='relu')(model2_hidden4)
	# model2_hidden6 = layers.Conv2D(64, kernel_size=(3, 3), strides=(2, 2),
	# 					 activation='relu')(model2_hidden5)
	model2_BN3 = layers.BatchNormalization()(model2_hidden5)
	model2_hidden6 = layers.MaxPool2D()(model2_BN3)

	model2_hidden7 = layers.Conv2D(128, kernel_size=(5, 5), strides=(1, 1),
						 activation='relu')(model2_hidden6)
	# model2_hidden8 = layers.Conv2D(128, kernel_size=(3, 3), strides=(2, 2),
	# 					 activation='relu')(model2_hidden7)
	model2_BN4 = layers.BatchNormalization()(model2_hidden7)
	model2_hidden8 = layers.MaxPool2D()(model2_BN4)

	model2_hidden9 = layers.Flatten()(model2_hidden8)
	# model2_hidden10 = layers.Dropout(0.2)(model2_hidden9)
	model2_hidden10 = layers.BatchNormalization()(model2_hidden9)
	model2_hidden11 = layers.Dense(128, activation='relu')(model2_hidden10)
	model2_output = layers.Dropout(0.2)(model2_hidden11)
	model2_output = layers.Dense(2, activation='softmax')(model2_output)

	model = Model(model2_input, model2_output)

	return model

def create_pause_model(n_features):
	model = tf.keras.Sequential()
	model.add(layers.Input(shape=(n_features,)))
	model.add(layers.BatchNormalization())
	model.add(layers.Dense(16, activation='relu'))
	model.add(layers.BatchNormalization())
	model.add(layers.Dropout(0.2))
	model.add(layers.Dense(16, activation='relu'))
	model.add(layers.BatchNormalization())
	model.add(layers.Dropout(0.2))
	model.add(layers.Dense(24, activation='relu'))
	model.add(layers.BatchNormalization())
	model.add(layers.Dropout(0.1))
	model.add(layers.Dense(24, activation='relu'))
	model.add(layers.BatchNormalization())
	model.add(layers.Dropout(0.1))
	model.add(layers.Dense(2, activation='softmax', kernel_regularizer=tf.keras.regularizers.l2(0.01), activity_regularizer=tf.keras.regularizers.l1(0.01)))
	return model

def create_compare_model(features_size):

	model = tf.keras.Sequential()
	model.add(layers.Input(shape=(features_size,)))

	model.add(layers.Dense(24, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(0.01), activity_regularizer=tf.keras.regularizers.l1(0.01)))
	model.add(layers.BatchNormalization())
	model.add(layers.Dropout(0.2))

	model.add(layers.Dense(32, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(0.01), activity_regularizer=tf.keras.regularizers.l1(0.01)))
	model.add(layers.BatchNormalization())
	model.add(layers.Dropout(0.3))

	model.add(layers.Dense(32, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(0.01), activity_regularizer=tf.keras.regularizers.l1(0.01)))
	model.add(layers.BatchNormalization())
	model.add(layers.Dropout(0.3))

	model.add(layers.Dense(24, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(0.01), activity_regularizer=tf.keras.regularizers.l1(0.01)))
	model.add(layers.BatchNormalization())
	model.add(layers.Dropout(0.2))

	model.add(layers.Dense(2, activation='softmax', kernel_regularizer=tf.keras.regularizers.l2(0.01), activity_regularizer=tf.keras.regularizers.l1(0.01)))

	return model

data = dataset.prepare_data('../ADReSS-IS2020-data/train')
X_intervention, X_pause, X_spec, X_compare, X_reg_intervention, X_reg_pause, X_reg_compare = data[0:7]
y, y_reg, filenames_intervention, filenames_pause, filenames_spec, filenames_compare = data[7:]

feature_types = {
	'intervention': X_intervention,
	'pause': X_pause,
	'spectogram': X_spec,
	'compare': X_compare
}

results = {}

model_types = ['intervention']
model_types = ['compare']
# model_types = ['pause']

model_dir = 'tuned_models'
model_dir = Path(model_dir)
model_dir.joinpath(model_types[0]).mkdir(parents=True, exist_ok=True)
model_dir = str(model_dir)

## Train Intervention, models saved in `model_dir/intervention_{fold}.h5`
for m in model_types:
	t_results, v_results = train_n_folds(m, feature_types[m], y, 5, model_dir)

print('trained ', model_types[0])
for i,j in enumerate(t_results):
	print('Fold_{}'.format(i))
	print('Training_accuracy ',j)
	print('Val_accuracy ',v_results[i])

print('Training accuracy mean', np.mean(t_results))
print('Training accuracy std', np.std(t_results))
print('Val accuracy mean', np.mean(v_results))
print('Val accuracy std', np.std(v_results))
