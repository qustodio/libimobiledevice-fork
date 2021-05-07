#!/bin/sh

export root_path=$PWD
export install_dir="$root_path/dependencies"
export tmp_dir="tmp"
export tmp_path="$root_path/$tmp_dir"

export openssl_url="https://www.openssl.org/source/openssl-1.1.1k.tar.gz"
export openssl_file="openssl-1.1.1k.tar.gz"
export openssl_dir="openssl-1.1.1k"
export openssl_check_file="${install_dir}/include/openssl/opensslv.h"
export libplist_url="https://github.com/libimobiledevice/libplist.git"
export libplist_dir="libplist"
export libplist_check_file="${install_dir}/lib/libplist.la"
export libusbmuxd_url="https://github.com/libimobiledevice/libusbmuxd.git"
export libusbmuxd_dir="libusbmuxd"
export libusbmuxd_check_file="${install_dir}/lib/libusbmuxd.la"
export libimobiledevice_url="https://github.com/libimobiledevice/libimobiledevice.git"
export libimobiledevice_dir="libimobiledevice"
export libimobiledevice_check_file="${install_dir}/lib/libimobiledevice.la"
BRANCH="master"

mkdir $tmp_dir
cd $tmp_path

## openssl
#if is not installed, install it
if [ ! -f $openssl_check_file ]; then
	echo "\n\n"
	echo "Install openssl"
	echo "-------------------------------------------\n\n"
	# download sources
	curl -OL $openssl_url
	tar xvzf $openssl_file
	# compile it
	cd $openssl_dir
	if [[ "$(uname -m)" == "x86_64" ]]; then
		echo "\n\n ------- Compiling Openssl with Darwin Intel ------- \n\n"
		./Configure --prefix=$install_dir --openssldir=$install_dir/openssl darwin64-x86_64-cc
	elif [[ "$(uname -m)" == "arm64" ]]; then
		echo "\n\n ------- Compiling Openssl with Darwin Apple Silicon ------- \n\n"
		./Configure --prefix=$install_dir shared enable-rc5 zlib darwin64-arm64-cc no-asm
	elif [[ "$(uname -s)" == *"CYGWIN"* ]]; then
		dos2unix ./*
		./Configure --prefix=$install_dir --openssldir=$install_dir/openssl Cygwin-x86_64
	else
		echo "\n\n ------- No suitable compiler has been found  ------- \n\n"
	fi
	make
	make install_sw
fi

## lipplist
# if is not installed, install it
if [ ! -f $libplist_check_file ]; then
	echo "\n\n"
	echo "Install libplist"
	echo "-------------------------------------------\n\n"
	# download sources
	cd $tmp_path
	git clone $libplist_url
	# compile it
	cd $libplist_dir
	git checkout $BRANCH
	# for some reason the first time it set the libtool folter to ../.. instead of .
	# so running a second time the issue its fixed
	if [[ "$(uname -s)" == *"CYGWIN"* ]]; then
		dos2unix ./*
	fi
	./autogen.sh
	./autogen.sh
	./configure --prefix=$install_dir
	make
	make install
	# this file was created the first time autogen.sh runs (in the wrong directory)
	rm ../../ltmain.sh
fi

## libusbmuxd
# if is not installed, install it
if [ ! -f $libusbmuxd_check_file ]; then
	echo "\n\n"
	echo "Install libusbmuxd"
	echo "-------------------------------------------\n\n"
	# download sources
	cd $tmp_path
	git clone $libusbmuxd_url
	# compile it
	cd $libusbmuxd_dir
	git checkout $BRANCH
	export PKG_CONFIG_PATH=$install_dir/lib/pkgconfig
	# for some reason the first time it set the libtool folter to ../.. instead of .
	# so running a second time the issue its fixed
	if [[ "$(uname -s)" == *"CYGWIN"* ]]; then
		dos2unix ./*
	fi
	./autogen.sh
	./autogen.sh
	./configure --prefix=$install_dir
	make
	make install
	# this file was created the first time autogen.sh runs (in the wrong directory)
	rm ../../ltmain.sh
fi

## libimobiledevice
# if is not installed, install it
if [ ! -f $libimobiledevice_check_file ]; then
	echo "\n\n"
	echo "Install libimobiledevice"
	echo "-------------------------------------------\n\n"
	cd $root_path
	# download sources
	# compile it
	export PKG_CONFIG_PATH=$install_dir/lib/pkgconfig
	export LD_LIBRARY_PATH=$install_dir/lib:$LD_LIBRARY_PATH
	export CPATH=$install_dir/include/openssl:$CPATH
	# for some reason the first time it set the libtool folter to ../.. instead of .
	# so running a second time the issue its fixed
	if [[ "$(uname -s)" == *"CYGWIN"* ]]; then
		dos2unix ./*
	fi
	./autogen.sh
	./autogen.sh
	./configure --prefix=$install_dir
	make
	make install
	rm ltmain.sh
	# this file was created the first time autogen.sh runs (in the wrong directory)
fi

# clean
cd $root_path
rm -rf $tmp_dir
# remove binaries, we don't need them

