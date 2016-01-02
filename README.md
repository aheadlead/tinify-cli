# tinify-cli

基于 Tinify 的批量图片压缩工具。

# 特性

* 支持多线程操作
* 支持多 API Key
* 支持正则匹配文件名, 并支持只预览文件名变化而不压缩的功能
* 支持批量验证 Key 的用量
* 支持除上传到 AWS S3 的所有的 tinyjpg 功能

# 如何开始

    $ python setup install
    $ tinify-cli -h  # 查看帮助

# 安装需求

* Python 2.7
* requests
* prettytable

# To-do

* 对目标位置已有的文件进行提示
* 提高带宽的利用率
* 英语支持

# 其他

MIT License

作者 aheadlead aheadlead@dlifep.com
