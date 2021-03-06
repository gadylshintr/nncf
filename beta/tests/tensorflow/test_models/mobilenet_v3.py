"""
 Copyright (c) 2020 Intel Corporation
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
      http://www.apache.org/licenses/LICENSE-2.0
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

from tensorflow.python.keras import backend
from tensorflow.python.keras import models
from tensorflow.python.keras.applications import imagenet_utils
from tensorflow.python.keras import layers


def MobileNetV3Small(input_shape=None):
    if input_shape is None:
        input_shape = (None, None, 3)

    if backend.image_data_format() == 'channels_last':
        row_axis, col_axis = (0, 1)
    else:
        row_axis, col_axis = (1, 2)
    rows = input_shape[row_axis]
    cols = input_shape[col_axis]
    if rows and cols and (rows < 32 or cols < 32):
        raise ValueError('Input size must be at least 32x32; got `input_shape=' +
                         str(input_shape) + '`')

    img_input = layers.Input(shape=input_shape)
    channel_axis = 1 if backend.image_data_format() == 'channels_first' else -1

    kernel = 5
    activation = hard_swish
    se_ratio = 0.25
    last_point_ch = 1024

    x = img_input
    x = layers.Rescaling(1. / 255.)(x)
    x = layers.Conv2D(
        16,
        kernel_size=3,
        strides=(2, 2),
        padding='same',
        use_bias=False,
        name='Conv')(x)
    x = layers.BatchNormalization(
        axis=channel_axis, epsilon=1e-3,
        momentum=0.999, name='Conv/BatchNorm')(x)
    x = activation(x)

    x = stack_fn(x, kernel, activation, se_ratio)

    last_conv_ch = _depth(backend.int_shape(x)[channel_axis] * 6)

    x = layers.Conv2D(
        last_conv_ch,
        kernel_size=1,
        padding='same',
        use_bias=False,
        name='Conv_1')(x)
    x = layers.BatchNormalization(
        axis=channel_axis, epsilon=1e-3,
        momentum=0.999, name='Conv_1/BatchNorm')(x)
    x = activation(x)
    x = layers.Conv2D(
        last_point_ch,
        kernel_size=1,
        padding='same',
        use_bias=True,
        name='Conv_2')(x)
    x = activation(x)

    x = layers.GlobalAveragePooling2D()(x)
    if channel_axis == 1:
        x = layers.Reshape((last_point_ch, 1, 1))(x)
    else:
        x = layers.Reshape((1, 1, last_point_ch))(x)
    x = layers.Dropout(0.2)(x)
    x = layers.Conv2D(1000, kernel_size=1, padding='same', name='Logits')(x)
    x = layers.Flatten()(x)
    x = layers.Activation(activation='softmax',
                          name='Predictions')(x)

    # Create model.
    return models.Model(img_input, x, name='MobilenetV3small')


def stack_fn(x, kernel, activation, se_ratio):
    x = _inverted_res_block(x, 1, _depth(16), 3, 2, se_ratio, relu, 0)
    x = _inverted_res_block(x, 72. / 16, _depth(24), 3, 2, None, relu, 1)
    x = _inverted_res_block(x, 88. / 24, _depth(24), 3, 1, None, relu, 2)
    x = _inverted_res_block(x, 4, _depth(40), kernel, 2, se_ratio, activation, 3)
    x = _inverted_res_block(x, 6, _depth(40), kernel, 1, se_ratio, activation, 4)
    x = _inverted_res_block(x, 6, _depth(40), kernel, 1, se_ratio, activation, 5)
    x = _inverted_res_block(x, 3, _depth(48), kernel, 1, se_ratio, activation, 6)
    x = _inverted_res_block(x, 3, _depth(48), kernel, 1, se_ratio, activation, 7)
    x = _inverted_res_block(x, 6, _depth(96), kernel, 2, se_ratio, activation, 8)
    x = _inverted_res_block(x, 6, _depth(96), kernel, 1, se_ratio, activation, 9)
    x = _inverted_res_block(x, 6, _depth(96), kernel, 1, se_ratio, activation, 10)
    return x


def relu(x):
    return layers.ReLU()(x)


def hard_sigmoid(x):
    return layers.ReLU(6.)(x + 3.) * (1. / 6.)


def hard_swish(x):
    return layers.Multiply()([hard_sigmoid(x), x])


def _depth(v, divisor=8, min_value=None):
    if min_value is None:
        min_value = divisor
    new_v = max(min_value, int(v + divisor / 2) // divisor * divisor)
    # Make sure that round down does not go down by more than 10%.
    if new_v < 0.9 * v:
        new_v += divisor
    return new_v


def _se_block(inputs, filters, se_ratio, prefix):
    x = layers.GlobalAveragePooling2D(name=prefix + 'squeeze_excite/AvgPool')(
        inputs)
    if backend.image_data_format() == 'channels_first':
        x = layers.Reshape((filters, 1, 1))(x)
    else:
        x = layers.Reshape((1, 1, filters))(x)
    x = layers.Conv2D(
        _depth(filters * se_ratio),
        kernel_size=1,
        padding='same',
        name=prefix + 'squeeze_excite/Conv')(
        x)
    x = layers.ReLU(name=prefix + 'squeeze_excite/Relu')(x)
    x = layers.Conv2D(
        filters,
        kernel_size=1,
        padding='same',
        name=prefix + 'squeeze_excite/Conv_1')(
        x)
    x = hard_sigmoid(x)
    x = layers.Multiply(name=prefix + 'squeeze_excite/Mul')([inputs, x])
    return x


def _inverted_res_block(x, expansion, filters, kernel_size, stride, se_ratio,
                        activation, block_id):
    channel_axis = 1 if backend.image_data_format() == 'channels_first' else -1
    shortcut = x
    prefix = 'expanded_conv/'
    infilters = backend.int_shape(x)[channel_axis]
    if block_id:
        # Expand
        prefix = 'expanded_conv_{}/'.format(block_id)
        x = layers.Conv2D(
            _depth(infilters * expansion),
            kernel_size=1,
            padding='same',
            use_bias=False,
            name=prefix + 'expand')(
            x)
        x = layers.BatchNormalization(
            axis=channel_axis,
            epsilon=1e-3,
            momentum=0.999,
            name=prefix + 'expand/BatchNorm')(
            x)
        x = activation(x)

    if stride == 2:
        x = layers.ZeroPadding2D(
            padding=imagenet_utils.correct_pad(x, kernel_size),
            name=prefix + 'depthwise/pad')(
            x)
    x = layers.DepthwiseConv2D(
        kernel_size,
        strides=stride,
        padding='same' if stride == 1 else 'valid',
        use_bias=False,
        name=prefix + 'depthwise')(
        x)
    x = layers.BatchNormalization(
        axis=channel_axis,
        epsilon=1e-3,
        momentum=0.999,
        name=prefix + 'depthwise/BatchNorm')(
        x)
    x = activation(x)

    if se_ratio:
        x = _se_block(x, _depth(infilters * expansion), se_ratio, prefix)

    x = layers.Conv2D(
        filters,
        kernel_size=1,
        padding='same',
        use_bias=False,
        name=prefix + 'project')(
        x)
    x = layers.BatchNormalization(
        axis=channel_axis,
        epsilon=1e-3,
        momentum=0.999,
        name=prefix + 'project/BatchNorm')(
        x)

    if stride == 1 and infilters == filters:
        x = layers.Add(name=prefix + 'Add')([shortcut, x])
    return x
