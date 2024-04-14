FROM nvcr.io/nvidia/l4t-ml:r32.6.1-py3

ENV PYTHON_VERSION=3.10

ENV DEBIAN_FRONTEND=noninteractive

# Fix numpy issues
ENV OPENBLAS_CORETYPE=AARCH64

# Install Python newer than 3.6
# https://github.com/deadsnakes/issues/issues/251
WORKDIR /work/
RUN apt-get update -y
RUN apt-get install -y tzdata curl ca-certificates gdebi-core
RUN curl -L -O https://github.com/bellflight/AVR-Python-arm-deb/releases/download/release/libpython3.10-minimal_3.10.11-1+bionic1_arm64.deb \
 && curl -L -O https://github.com/bellflight/AVR-Python-arm-deb/releases/download/release/libpython3.10-stdlib_3.10.11-1+bionic1_arm64.deb \
 && curl -L -O https://github.com/bellflight/AVR-Python-arm-deb/releases/download/release/python3.10-distutils_3.10.11-1+bionic1_all.deb \
 && curl -L -O https://github.com/bellflight/AVR-Python-arm-deb/releases/download/release/python3.10-lib2to3_3.10.11-1+bionic1_all.deb \
 && curl -L -O https://github.com/bellflight/AVR-Python-arm-deb/releases/download/release/python3.10-minimal_3.10.11-1+bionic1_arm64.deb \
 && curl -L -O https://github.com/bellflight/AVR-Python-arm-deb/releases/download/release/python3.10_3.10.11-1+bionic1_arm64.deb
RUN dpkg -i libpython3.10-minimal_3.10.11-1+bionic1_arm64.deb \
 && dpkg -i libpython3.10-stdlib_3.10.11-1+bionic1_arm64.deb \
 && dpkg -i python3.10-lib2to3_3.10.11-1+bionic1_all.deb \
 && dpkg -i python3.10-distutils_3.10.11-1+bionic1_all.deb \
 && dpkg -i python3.10-minimal_3.10.11-1+bionic1_arm64.deb \
 && dpkg -i python3.10_3.10.11-1+bionic1_arm64.deb \
 && rm *.deb
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python${PYTHON_VERSION} \
 && python${PYTHON_VERSION} -m pip install pip wheel setuptools --upgrade

WORKDIR /app

# Install OpenSSL and related dependencies
RUN apt-get install -y libssl-dev

# Copy libraries
COPY c/libraries c/libraries

# Set the OpenSSL root directory
ENV OPENSSL_ROOT_DIR=/usr/include/openssl

# Install paho C library
RUN cd c/libraries/paho.mqtt.c \
 && cmake -Bbuild -H. -DPAHO_BUILD_STATIC=ON -DPAHO_WITH_SSL=ON -DPAHO_HIGH_PERFORMANCE=ON \
 && cmake --build build/ --target install \
 && ldconfig
# Install paho C++ library
RUN cd c/libraries/paho.mqtt.cpp \
 && cmake -Bbuild -H. -DPAHO_BUILD_STATIC=ON \
 && cmake --build build/ --target install \
 && ldconfig
# RUN git clone https://github.com/NVIDIA-AI-IOT/isaac_ros_apriltag \
#  && cd isaac_ros_apriltag \
#  && git checkout v0.9.0-ea1 \
#  && cp -r isaac_ros_apriltag/nvapriltags/lib_aarch64_jetpack44 ../c/libraries/lib_aarch64_jetpack44
RUN wget https://developer.nvidia.com/isaac/download/third_party/april_tags_v5_jp44_nano-tar-xz \
 && tar -xf april_tags_v5_jp44_nano-tar-xz --directory c/libraries \
 && rm april_tags_v5_jp44_nano-tar-xz
# Build the april tag application
COPY c/src c/src
COPY c/CMakeLists.txt c/CMakeLists.txt

# Download and install VPI dependencies
RUN wget https://repo.download.nvidia.com/jetson/common/pool/main/libc/libcufft/libcufft-10-2_10.1.2.300-1_arm64.deb \
 && wget https://repo.download.nvidia.com/jetson/common/pool/main/c/cuda/cuda-license-10-0_10.0.326-1_arm64.deb \
 && wget https://repo.download.nvidia.com/jetson/common/pool/main/c/cuda/cuda-cufft-10-0_10.0.326-1_arm64.deb \
 && wget https://repo.download.nvidia.com/jetson/common/pool/main/c/cuda/cuda-cudart-10-0_10.0.326-1_arm64.deb
RUN gdebi --non-interactive libcufft-10-2_10.1.2.300-1_arm64.deb \
 && gdebi --non-interactive cuda-license-10-0_10.0.326-1_arm64.deb \
 && gdebi --non-interactive cuda-cufft-10-0_10.0.326-1_arm64.deb \
 && gdebi --non-interactive cuda-cudart-10-0_10.0.326-1_arm64.deb \
 && rm *.deb
# Download and install NVIDIA VPI & friends
RUN wget https://repo.download.nvidia.com/jetson/common/pool/main/libn/libnvvpi1/libnvvpi1_1.1.15_arm64.deb \
 && wget https://repo.download.nvidia.com/jetson/common/pool/main/v/vpi1-demos/vpi1-demos_1.1.15_arm64.deb \
 && wget https://repo.download.nvidia.com/jetson/common/pool/main/v/vpi1-dev/vpi1-dev_1.1.15_arm64.deb \
 && wget https://repo.download.nvidia.com/jetson/common/pool/main/p/python-vpi1/python-vpi1_1.1.15_arm64.deb \
 && wget https://repo.download.nvidia.com/jetson/common/pool/main/v/vpi1-samples/vpi1-samples_1.1.15_arm64.deb
RUN gdebi --non-interactive libnvvpi1_1.1.15_arm64.deb \
 && gdebi --non-interactive vpi1-demos_1.1.15_arm64.deb \
 && gdebi --non-interactive vpi1-dev_1.1.15_arm64.deb \
 && gdebi --non-interactive python-vpi1_1.1.15_arm64.deb \
 && gdebi --non-interactive vpi1-samples_1.1.15_arm64.deb \
 && rm *.deb
# Download extra cuda kits (I hate it here ._.)
RUN wget https://repo.download.nvidia.com/jetson/common/pool/main/c/cuda-cuobjdump/cuda-cuobjdump-10-2_10.2.300-1_arm64.deb
RUN wget https://repo.download.nvidia.com/jetson/common/pool/main/c/cuda/cuda-cudart-dev-10-0_10.0.326-1_arm64.deb
RUN wget https://repo.download.nvidia.com/jetson/common/pool/main/c/cuda-nvcc/cuda-nvcc-10-2_10.2.300-1_arm64.deb
RUN wget https://repo.download.nvidia.com/jetson/common/pool/main/c/cuda-compiler-10-2/cuda-compiler-10-2_10.2.460-1_arm64.deb
RUN wget https://repo.download.nvidia.com/jetson/common/pool/main/c/cuda/cuda-toolkit-10-0_10.0.326-1_arm64.deb

RUN gdebi --non-interactive cuda-cuobjdump-10-2_10.2.300-1_arm64.deb
RUN gdebi --non-interactive cuda-cudart-dev-10-0_10.0.326-1_arm64.deb
RUN gdebi --non-interactive cuda-nvcc-10-2_10.2.300-1_arm64.deb
RUN gdebi --non-interactive cuda-compiler-10-2_10.2.460-1_arm64.deb
RUN gdebi --non-interactive cuda-toolkit-10-0_10.0.326-1_arm64.deb

RUN rm *.deb

RUN mkdir -p c/build \
 && cd c/build \
 && cmake .. \
 && make -j$(nproc)

COPY python/requirements.txt python/requirements.txt
RUN python3.10 -m pip install -r python/requirements.txt
COPY . .

RUN chmod +x ./docker-entrypoint.sh
RUN rm /usr/bin/python3 && ln -s /usr/bin/python${PYTHON_VERSION} /usr/bin/python3
CMD ["./docker-entrypoint.sh"]