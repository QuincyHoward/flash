"""
output_processors 测试包

测试内容：
  - hdf5processor 子模块测试
  - loader 子模块测试
  - plotter 子模块测试
  - 集成测试

运行方式：
  # 运行所有测试
  pytest output_processors/test/ -v
  
  # 运行单个测试文件
  pytest output_processors/test/test_hdf5processor.py -v
  
  # 运行单个测试类
  pytest output_processors/test/test_hdf5processor.py::TestFlashHDF5File -v
  
  # 运行单个测试
  pytest output_processors/test/test_hdf5processor.py::TestFlashHDF5File::test_load_file -v
"""

__version__ = "1.0.0"
