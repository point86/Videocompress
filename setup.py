from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need
# fine tuning.
buildOptions = dict(packages = [], excludes = [])

import sys
base = 'Win32GUI' if sys.platform=='win32' else None

executables = [
    Executable('videocompress.py', base=base)
]

setup(name='Videocompress',
      version = '0.5',
      description = 'A simple utility that runs ffmpeg over an entire directory (and subfolders).',
      options = dict(build_exe = buildOptions),
      executables = executables)
