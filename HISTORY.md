## 2012-03-29
* 新功能：任务延时/任务完成后执行命令

## 2012-01-12
* 修复x264 tMod 2140的兼容性问题

## 2012-01-01
* 自动根据源文件名称搜索qpfile/zones/timecode

## 2011-08-19

* Bug修复
* 如在参数中指定音频，则在1pass自动禁用以防止错误（可使用--1pass-same-extra-args禁用此行为）

## 2011-08-15

* 任务系统显示增强
    ^ 控制台标题栏显示整体及运行中任务进度
    ^ 任务完成后在信息输出中显示码率及fps

## 2011-08-12

* 以彩色输出任务列表
* 修复：1pass任务有时会在完成时卡死

## 2011-08-05

* 修复任务系统与额外参数的冲突

## 2011-08-04

* 新增任务系统，默认可同时运行两个1pass任务，并于所有1pass完成后再逐个运行2pass任务。简单命令说明请参考encx264.py !task help
* 可于target内指定x264路径，可参考sample设置

* 本版本无法从旧版自动更新，请下载完整版

## 2011-04-11

* 新参数：--inFile-2pass * ：2pass时使用另一个avs脚本
* 参数现在对大小写不敏感了

## 2011-03-15

* 默认不记录压制进度，减小log体积

## 2011-03-14

* 支持指定x264优先级
* 支持1pass压制，把target内的2pass参数删除即可
* 支持脚本自动更新

## 2011-03-06

* 可直接在命令行附加x264参数

## 2011-03-03

* 修正路径内不能包含空格的问题
