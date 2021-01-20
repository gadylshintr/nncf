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

from beta.nncf.api.compression import CompressionAlgorithmBuilder
from beta.nncf.api.compression import CompressionAlgorithmController
from beta.nncf.tensorflow.graph.transformations.layout import TransformationLayout
from beta.nncf.utils.logger import logger
from nncf.common.utils.registry import Registry


TF_COMPRESSION_ALGORITHMS = Registry('compression algorithm')


@TF_COMPRESSION_ALGORITHMS.register('NoCompressionAlgorithm')
class NoCompressionAlgorithmBuilder(CompressionAlgorithmBuilder):
    def get_transformation_layout(self, _):
        return TransformationLayout()


class NoCompressionAlgorithmController(CompressionAlgorithmController):
    pass


def get_compression_algorithm_builder(config):
    algorithm_key = config.get('algorithm', 'NoCompressionAlgorithm')
    logger.info('Creating compression algorithm: {}'.format(algorithm_key))
    return TF_COMPRESSION_ALGORITHMS.get(algorithm_key)
