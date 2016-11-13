#!/bin/bash

apt-get update

cd /root
mkdir opencv
cd opencv

pip3 install numpy
apt-get install -yy build-essential cmake pkg-config \
    libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev \
    libavcodec-dev libavformat-dev libswscale-dev libv4l-dev \
    libxvidcore-dev libx264-dev libgtk2.0-dev \
    libatlas-base-dev gfortran \
    python3-dev \
    libav-tools

wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/master.zip
wget -O opencv.zip https://github.com/opencv/opencv/archive/master.zip
#wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.1.0.zip
#wget -O opencv.zip https://github.com/Itseez/opencv/archive/3.1.0.zip

unzip opencv.zip
unzip opencv_contrib.zip

#cd opencv-3.1.0
cd opencv-master
mkdir build
cd build
cmake \
    -D WITH_FFMPEG=1 \
    -D ENABLE_NEON=ON \
    -D WITH_LIBV4L=ON \
    -D BUILD_WITH_DEBUG_INFO=OFF \
	-D BUILD_DOCS=OFF \
	-D BUILD_EXAMPLES=OFF \
	-D BUILD_TESTS=OFF \
	-D BUILD_opencv_ts=OFF \
	-D BUILD_PERF_TESTS=OFF \
	-D INSTALL_C_EXAMPLES=OFF \
    -D OPENCV_EXTRA_MODULES_PATH=~/opencv/opencv_contrib-master/modules \
    -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=$(python3 -c "import sys; print(sys.prefix)") \
    -D PYTHON_EXECUTABLE=$(which python3) ..

make -j4
make install
mv /usr/lib/python3.4/dist-packages/cv2.cpython-34m.so /usr/lib/python3.4/dist-packages/cv2.so
ldconfig
