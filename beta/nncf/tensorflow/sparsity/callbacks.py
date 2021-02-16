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

from typing import Callable

import tensorflow as tf

from beta.nncf.tensorflow.callbacks.statistics_callback import StatisticsCallback
from beta.nncf.tensorflow.sparsity.utils import convert_raw_to_printable
from beta.nncf.tensorflow.sparsity.utils import prepare_for_tensorboard


class UpdateMask(tf.keras.callbacks.Callback):
    def __init__(self, scheduler):
        super().__init__()
        self._scheduler = scheduler

    def on_train_batch_begin(self, batch, logs=None):
        self._scheduler.step()

    def on_epoch_begin(self, epoch, logs=None):
        self._scheduler.epoch_step(epoch)


class SparsityStatisticsCallback(StatisticsCallback):
    """
    Callback for logging sparsity compression statistics to tensorboard and stdout
    """

    def __init__(self,
                 raw_statistics_fn: Callable[[], dict],
                 log_tensorboard: bool = True,
                 log_text: bool = True,
                 log_dir: str = None):
        """
        :param raw_statistics_fn: callable to evaluate raw sparsity compression statistics
        :param log_tensorboard: whether to log statistics to tensorboard or not
        :param log_text: whether to log statistics to stdout
        :param log_dir: the directory for tensorbard logging
        """
        super().__init__(raw_statistics_fn, log_tensorboard, log_text, log_dir)

    def _prepare_for_tensorboard(self, raw_statistics: dict):
        return prepare_for_tensorboard(raw_statistics)

    def _convert_raw_to_printable(self, raw_statistics: dict):
        return convert_raw_to_printable(raw_statistics)
