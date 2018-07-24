import numpy as np
import random
import hashlib

scale = 1000

def pack_weights(weights):
    packed_weights = []
    for matrix in weights:
        packed_weights.extend(matrix.flatten())
    return list(map(lambda x: int(x*scale), packed_weights))

def unpack_weights(weights, sizes):
    weights = list(map(lambda x: float(x*1.0/scale), weights))
    unpacked_weights = []
    base = offset = 0
    for x, y in zip(sizes[:-1], sizes[1:]):
        offset += x * y
        unpacked_weights.append(np.array(weights[base:offset]).reshape(y,x))
        base += offset
    return unpacked_weights

import mnist_loader
training_data, validation_data, test_data = mnist_loader.load_data_wrapper()

import network
sizes = [784, 30, 10]
net = network.Network(sizes)
net.SGD(training_data[:5000], 1, 10, 3.0, test_data=test_data[:5000])

print hashlib.sha1(str(net.get_weights())).hexdigest()
"""
print unpack_weights(pack_weights(net.get_weights()),sizes)

untouched = net.get_weights()
processed = unpack_weights(pack_weights(net.get_weights()), sizes)

#always false due to scaling information loss
print np.array_equal(untouched, processed)"""
