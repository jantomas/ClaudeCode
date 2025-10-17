#!/bin/bash

if [ true ]; then
  # get a current python3
  
  sudo apt-get install wget build-essential libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev libffi-dev zlib1g-dev liblzma-dev -y
  VERSION=3.11.1
  VERSION_SHORT=3.11
  
  mkdir -p tmp
  cd tmp
  
  if [ ! -f Python-${VERSION}.tgz ]; then
    wget -O Python-${VERSION}.tgz https://www.python.org/ftp/python/${VERSION}/Python-${VERSION}.tgz
  fi
  
  tar xzf Python-${VERSION}.tgz
  cd Python-${VERSION}
  if [ ! -f python ]; then
    ./configure --enable-optimizations
  fi
  echo "### make altinstall"
  sudo make altinstall
  sudo update-alternatives --install /usr/bin/python python /usr/local/bin/python${VERSION_SHORT} 1
  
  echo "### install pip"
  /usr/local/bin/python${VERSION_SHORT} -m pip install --upgrade pip
  sudo update-alternatives --install /usr/bin/pip pip /usr/local/bin/pip${VERSION_SHORT} 1
  
  cd ..
fi