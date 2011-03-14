某SAP的x264压制脚本

### 脚本主要功能

* 支持1Pass crf + 2Pass bitrate模式，自动获取crf出来的码率作为2pass参数
* 自动记录压制log
* 多target支持，脚本内可定义多套预置参数

### 脚本需求

Python 3

### 基本用法

脚本放到x264目录，然后使用以下格式执行命令即可开始压制：

encx264.py <target> xxxx.avs xxxx.mp4 <crf> --tc ""

其中<target>为脚本内定义的target名字，后面的--tc ""是禁用输入timecode（因为我做的片子全部是VFR，为了偷懒脚本默认会使用脚本目录下的timecode.txt作为输入timecode，如果找不到就会报错）

target的定义方法请参考encx264_targets.py内现有的target，注意花括号参数会在运行时替换为实际值。最终传给x264的参数由公共参数和target特定参数组成。

### 脚本可选参数

*  --bitrate *：强制指定码率，适用于1pass不是crf的target
*  --sar：指定sar，注意如果target内没有default_sar，不在命令行指定sar会报错
*  --ref *：指定ref，如忽略脚本会使用target指定的default_ref
*  --pass 2：跳过1pass，如之前用脚本运行过1pass，码率会从记录文件内读取，否则需要用--bitrate指定码率
*  --tc "xxxx.txt"：指定输入timecode，忽略的话脚本会使用avs目录下的timecode.txt，找不到就会报错。如要禁用输入timecode，指定--tc ""
*  --bitrate-ratio *：2pass和1pass的码率比例，默认为1.0（即使用一样的码率）
*  --priority [idle|below_normal|normal|above_normal|high]：指定x264进程优先级
*  -- [参数]：在--后面的所有参数都会直接添加到x264命令行，例：

    encx264.py <....> -- --vf resize:640x480
    
### 自动更新

运行以下命令，即可将脚本更新至最新稳定版：
    encx264.py !update