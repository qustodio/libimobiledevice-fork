#!/usr/bin/env python
from __future__ import unicode_literals
import os
import platform
import re
import glob
import shutil
import json

from shell import shell, make

def get_relative_path(path: str) -> str:
    dirname = os.path.dirname(__file__)
    return os.path.join(dirname, path)


DEPENDENCIES_FILE = get_relative_path('dependencies.json')


def get_dependencies():
    with open(DEPENDENCIES_FILE) as file:
        return json.loads(file.read())['dependencies']


_openssl = None
_libplist = None
_libusbmuxd = None
_libimobiledevice_glue = None

for dependency in get_dependencies():
    if dependency['name'] == 'openssl':
        _openssl = dependency
    if dependency['name'] == 'libplist':
        _libplist = dependency
    if dependency['name'] == 'libusbmuxd':
        _libusbmuxd = dependency
    if dependency['name'] == 'libimobiledevice-glue':
        _libimobiledevice_glue = dependency

ROOT_PATH = os.getcwd()
INSTALL_DIR = f'{ROOT_PATH}/dependencies'
TMP_PATH = f'{ROOT_PATH}/tmp'

OPENSSL_URL = _openssl['url']
OPENSSL_CHECK_FILE = f'{INSTALL_DIR}/include/openssl/opensslv.h'

LIBPLIST_URL = _libplist['url']
LIBPLIST_COMMIT = _libplist['commit']

LIBUSBMUXD_URL = _libusbmuxd['url']
LIBUSBMUXD_COMMIT = _libusbmuxd['commit']

LIBIMOBILEDEVICE_GLUE_URL = _libimobiledevice_glue['url']
LIBIMOBILEDEVICE_GLUE_COMMIT = _libimobiledevice_glue['commit']

OPERATING_SYSTEM = platform.system()


def get_title(name: str) -> str:
    return f"""
                Install {name}
    -------------------------------------------


    """


def get_install_successfully(name: str) -> str:
    return f"""
            🥳 {name} installed successfully
    """


def exit_with_error(error: str):
    print(error)
    exit(1)


def configure_openssl(prefix:str, arch: str, openssl_dir: str = None) -> str:
    if openssl_dir:
        return f"./Configure --prefix={prefix} --openssldir={openssl_dir} {arch}"
    else:
        return f'./Configure --prefix={prefix} {arch}'


def get_openssl_configuration() -> str:
    operating_system = OPERATING_SYSTEM

    if operating_system == 'Darwin':
        arch = platform.machine()
        if arch == 'x86_64':
            print('\n\n ------- Compiling Openssl with Darwin Intel ------- \n\n')
            return configure_openssl(prefix=INSTALL_DIR, openssl_dir=f'{INSTALL_DIR}/openssl', arch='darwin64-x86_64-cc')
        elif arch == 'arm64':
            print('\n\n ------- Compiling Openssl with Darwin Apple Silicon ------- \n\n')
            return configure_openssl(prefix=INSTALL_DIR, arch='darwin64-arm64-cc')
        else:
            exit_with_error('\n\n ------- Invalid architecture found  ------- \n\n')
    elif operating_system.find('MINGW64') > -1:
        print('\n\n ------- Compiling Windows MINGW ------- \n\n')
        return configure_openssl(prefix=INSTALL_DIR, arch='mingw64')
    elif operating_system.find('MINGW32') > -1:
        return configure_openssl(prefix=INSTALL_DIR, arch='mingw32')
    else:
        exit_with_error('\n\n ------- No suitable compiler has been found  ------- \n\n')


def install_openssl_ifneeded():
    if os.path.isfile(OPENSSL_CHECK_FILE):
        return

    print(get_title('openssl'))

    if shutil.which('openssl') is not None:
        print('Openssl already installed')
        return

    openssl_tar_file = re.search('openssl-.*', OPENSSL_URL)[0]
    openssl_dir = f"{TMP_PATH}/{openssl_tar_file.replace('.tar.gz', '').strip()}"
    shell(f'curl -OL {OPENSSL_URL}', cwd=TMP_PATH)
    shell(f'tar xvzf {openssl_tar_file}', cwd=TMP_PATH)

    shell(get_openssl_configuration(), cwd=openssl_dir)

    make(cwd=openssl_dir)
    make('install_sw', cwd=openssl_dir)

    print(get_install_successfully('openssl'))


def install_lib_ifneeded(name: str, url: str, commit: str, is_pkg_config: bool = False, is_ld_library: bool = False, is_cdpath: bool = False):
    
    if glob.glob(f'{INSTALL_DIR}/lib/{name}-*'):
        return

    print(get_title(name))
    lib_dir = f'{TMP_PATH}/{name}'

    if not os.path.isdir(f'{TMP_PATH}/{name}'):
        shell(f'git clone {url} {name}', cwd=TMP_PATH)
        shell(f'git checkout {commit}', cwd=lib_dir)

    environment = os.environ.copy()
    openssl_path = shutil.which('openssl')
    if is_pkg_config:
        if openssl_path is not None:
            environment['PKG_CONFIG_PATH'] = f'{INSTALL_DIR}/lib/pkgconfig:/mingw64/lib/pkgconfig'
        else:
            environment['PKG_CONFIG_PATH'] = f'{INSTALL_DIR}/lib/pkgconfig'

    environment['CPATH'] = f'{INSTALL_DIR}/include/openssl'
            

    operating_system = OPERATING_SYSTEM
    if operating_system == 'Darwin':
        # For some reason the first time it set the libtool folter to ../.. instead of .
        # so running a second time the issue its fixed
        shell('./autogen.sh', cwd=lib_dir, check=False, env=environment)
        shell('./autogen.sh', cwd=lib_dir, env=environment)
        shell(f'./configure --prefix={INSTALL_DIR} --without-cython', cwd=lib_dir, env=environment)
    elif operating_system.find('MINGW') > -1:
        shell(f'./autogen.sh CC=gcc CXX=g++ --prefix={INSTALL_DIR} --without-cython --enable-debug', cwd=lib_dir, env=environment)

    make(cwd=lib_dir, env=environment)
    make('install', cwd=lib_dir, env=environment)

    ltmain = 'ltmain.sh'
    if os.path.isfile(ltmain):
        os.remove(ltmain)

    print(get_install_successfully(name))


def install_name_tool(option: str, library: str, binary_or_library: str):
    library_dir=f'{INSTALL_DIR}/lib'
    shell(f'install_name_tool {option} {library_dir}/{library} @loader_path/{library} {library_dir}/{binary_or_library}')


def change_dylib_path_to_relative():
    libssl='libssl.1.1.dylib'
    libcrypto='libcrypto.1.1.dylib'
    libplist='libplist-2.0.3.dylib'
    libusbmuxd='libusbmuxd-2.0.6.dylib'
    libimobiledevice='libimobiledevice-1.0.6.dylib'

    print("""
       Change absolute path to relative path
    -------------------------------------------
    """)

    print(f'✅ {libssl}\n')
    install_name_tool('-change', libcrypto, libssl)

    print(f'✅ {libusbmuxd}\n')
    install_name_tool('-change', libplist, libusbmuxd)

    print(f'✅ {libimobiledevice}\n')
    for library in [libssl, libcrypto, libplist, libusbmuxd]:
        install_name_tool('-change', library, libimobiledevice)


def build_libimobiledevice():
    print(get_title('libimobiledevice'))
    environment = os.environ.copy()
    openssl_path = shutil.which('openssl')
    if openssl_path is not None:
        environment['PKG_CONFIG_PATH'] = f'{INSTALL_DIR}/lib/pkgconfig:/mingw64/lib/pkgconfig'
    else:
        exit('OpenSSL not found!')

    environment['LD_LIBRARY_PATH'] = f'{INSTALL_DIR}/lib'

    if OPERATING_SYSTEM.find('MINGW64') > -1:
        shell(f'cp /mingw64/lib/libssl.dll.a /mingw64/lib/libcrypto.dll.a {INSTALL_DIR}/lib')
        shell(f'cp /mingw64/bin/libssl*.dll /mingw64/bin/libcrypto*.dll {INSTALL_DIR}/lib')

    build_path = f'{ROOT_PATH}/build'
    shell(f'./autogen.sh CC=gcc CXX=g++ --prefix={build_path} --without-cython --enable-debug', env=environment)
    make(env=environment)
    make('install', env=environment)

    shell(F'cp {INSTALL_DIR}/lib/*.dll {build_path}/bin')


# RUN SCRIPT
if __name__ == "__main__":
    print('ROOT_PATH: ', ROOT_PATH)

    if not os.path.isdir(INSTALL_DIR):
        print("🛠 Don't worry building it for you...")
        os.mkdir(TMP_PATH)

    # Install Openssl
    install_openssl_ifneeded()

    # Install libimobledevice tools and library
    install_lib_ifneeded('libplist', LIBPLIST_URL, LIBPLIST_COMMIT)
    install_lib_ifneeded('libimobiledevice-glue', LIBIMOBILEDEVICE_GLUE_URL, LIBIMOBILEDEVICE_GLUE_COMMIT, is_pkg_config=True)
    install_lib_ifneeded('libusbmuxd', LIBUSBMUXD_URL, LIBUSBMUXD_COMMIT, is_pkg_config=True)

    if os.path.isdir(TMP_PATH):
        shutil.rmtree(TMP_PATH)

    if os.path.isdir(f'{INSTALL_DIR}/bin'):
        if OPERATING_SYSTEM.find('MINGW') > -1:
            shell("cp dependencies/bin/*.dll dependencies/lib")
        shutil.rmtree(f'{INSTALL_DIR}/bin')

    build_libimobiledevice()

    if OPERATING_SYSTEM == "Darwin":
        change_dylib_path_to_relative()
