# ECHO-7 / MTRX3700：视觉引导车位搜索与停靠

[中文](README.md) | [English](README_EN.md)

正式工程是 `quartus/PartBDebug.qpf`，顶层是 `echo7IntegratedTop`，器件是 DE1-SoC 的 Cyclone V `5CSEMA5F31C6`。同一个 SOF 提供真实视觉调试、合成视觉底盘调试和整机运行。目标只能由实体 SW0–SW5 选择；JTAG 不提供直接轮速或假超声距离入口。

本次构建、下载和实机测试的具体结果见 [本次修复验收记录](docs/REPAIR_RESULT.md)。旧版本的拟合、仿真和实拍记录保留其历史含义，不代表当前代码已经完成实车验收。原始来源与成员归属见 [OWNERS.md](OWNERS.md)。麦克风和语音识别已取消。红1保留自动校色；按本次追加需求，红2在非活动任务时重新读取当前实体拨码、重锁并请求启动。

## 当前版本与验收范围

当前生产源码标识为 **E7070004**，CCTL接口标识仍为 **E7070001**。两者是不同用途的版本号。迭代关系见 [版本记录](VERSION_README.md)，可复核的命令、用时和实机记录见 [修复记录](docs/REPAIR_RESULT.md)。

| 版本 | 该版关键变化 | 已取得的结果 |
|---|---|---|
| E7070002 | 三模式、实体独热选择、红2事件、完整安全链、分页视觉诊断 | Full Compilation和R6通过；实板注入、轮向、IR和真实蓝1追踪通过；之后发现单帧溢出历史位会永久阻断C |
| E7070003 | 将可恢复坏帧与历史故障位分离，接收时刻建立恢复边界 | 236项控制检查、R6和Full Compilation通过；实板保留faultFlags=3仍恢复健康锁定；23个真实不同帧中22次锁定；发现红2未标定启动过早 |
| E7070004 | 未扫描标定时，红2pending等待新请求的三帧目标锁定 | **254项定向检查PASS；正式R6 219.556074秒，12项及CAUGHT全部PASS；Full Compilation和实际下载PASS；用户实物确认红2启动、蓝1离开后停车**。主机2秒STOP的独立物理停车时刻未验证；末状态VISION_ONLY、未ARM、逻辑零速，用户确认已停止 |

已经完成真实硬件纠正，不等于六车位落地闭环和地面360°扫描均已验收。上述实机主要在底盘架空条件下完成；本README把现有实现、对应版本的实际证据和后续操作分别说明。后续复现实验的操作步骤也不代表已执行结果。

## 环境与硬件前提

| 项目 | 本次使用/要求 |
|---|---|
| FPGA / 工程 | DE1-SoC，Cyclone V 5CSEMA5F31C6；`quartus/PartBDebug.qpf` |
| 综合与下载 | Quartus Prime Lite **18.1.0 Build 625**，Quartus STP与USB-Blaster驱动 |
| 主机脚本 | **Python 3.13**；按`requirements.txt`安装工程依赖 |
| 正式R6仿真 | **Verilator 5.050**、Bash、GNU Make及兼容C++编译器；本机Git Bash + MSYS2 MinGW编译器，`--jobs 4` |
| 定向RTL仿真 | ModelSim Altera Starter Edition **10.5b（2016.10）**；其通过不替代正式R6 |
| 视觉输入 | 实际OV7670相机、工程既有相机连接和正式标牌；VGA用于实时画面/诊断 |
| 运动与保护 | UGV02底盘UART、真实IR接收器、J3 RCWL-1601测距、3.3 V接口及共地 |

本机工作目录是 `C:\Quartus_Projects\ECHO72.0\github_publish\MTRX3700_MajorProject`。其他机器按实际克隆目录修改命令。首次使用确认相机、电源、地线、UART交叉连接和J3有效回波；先架空核对轮向，再开展地面测试。VISION_ONLY可在J3未连接时调视觉；两种可运动模式都需要真实有效的测距和IR安全条件。没有新增J4传感器，也没有通过JTAG伪造测距来绕过保护。

`status --watch`和注入各自持有JTAG会话。结束一个会话后再运行另一个命令，避免把链路占用误判为板上故障。具体引脚见本文末尾。

## 开关、按键与显示

| 操作 | 当前功能 |
|---|---|
| SW0 / SW1 / SW2 / SW3 / SW4 / SW5 | 分别选择蓝色车位1 / 2 / 3 / 4 / 5 / 6，必须恰好一位为1 |
| SW6 | 候选框及局部 RGB/HSV、颜色、数字和拒绝原因诊断；两页各8槽自动轮播，覆盖全部16候选 |
| SW7 | 中心小框采样及覆盖目标诊断 |
| SW8 | Bounding Box / perspective bypass；使用同一控制和安全链，版本切换后重新确认观测 |
| SW9 | 原始相机显示；立即取消运动授权，关闭后仍需重新 START/POWER |
| IR POWER `0x12` | 无急停时启动满足条件的新任务；活动任务中不重置扫描预算 |
| IR A `0x0F` | 锁存急停，立即撤销运动许可 |
| 红1牌与配对蓝色参考条 | 自动建立颜色采样窗口，完成校色；参考条不是蓝色车位编号 |
| 红2牌 | 连续确认后，重新SELECT当前合法拨码；未标定时等待新目标三帧锁定再启动，VISION_ONLY只重锁 |
| 急停后的 POWER | 第一次新按压仅解除 IR 锁存，仍停车；松开后再次按压才能启动 |
| KEY0 | 全局复位；回到 INTEGRATED、DISARMED、零速，重新选择/校色及扫描标定状态 |
| KEY1 | HEX 距离 / NEC高16位 / NEC低16位分页，并保留相机快照功能 |

六位开关整体稳定约20 ms后建立选择。全0为 `NO_SELECTION`，多位1为 `SELECTION_CONFLICT`，均清除旧追踪且不能运动。合法选择未启动时也会真实追踪，便于独立调视觉；红2可以重新建立同一拨码的请求边界。运动中同步后的开关组合改变，先停车并取消旧任务，新选择还需新启动。

HEX4显示模式：`0` INTEGRATED、`1` VISION_ONLY、`2` CHASSIS_INJECT。HEX5在无选择时显示 `n`，冲突时显示 `C`，其余显示距离页 `d` 或 NEC 页 `H/L`。HEX3–0显示毫米距离或对应NEC数据，无效距离留空。完整状态名称、选定编号和故障原因通过 `status` 读取。

读距离时只看`d`页右侧四位HEX3–HEX0，数值为**十进制毫米**。例如`d2 0520`表示距离520 mm（52.0 cm），左侧`d2`是“距离页＋CHASSIS_INJECT模式”，不能一起当成距离数字。按KEY1在`d → H → L`之间换页；H/L右四位是遥控NEC码的十六进制数据，不是测距值。距离无效时右四位全部熄灭，不应把空白读成0 mm。

显示、控制器和JTAG状态使用同一份超声`distance_mm`，传感器约每100 ms产生一次新测量；JTAG读取时刻不同，快照可能与眼前显示相差一次更新。毫米是代码定义的单位，尚不保证与尺子的绝对精度一致。现场调整反射板摆位后读数曾从379 mm变为520/521 mm，反射面和尺子测量起点尚未核定；不能据此修改换算系数或宣称已完成距离标定。

LEDR0运动许可，1 IR急停，2距离有效，3已停靠，4超声HOLD，5 UART忙，6/7 NEC完整帧/重复帧，8已确认目标，9未授权且距离有效。`LEDR0=0`、零速JSON已经发完、车体物理停稳是三件不同的事。NEC重复帧和连续重发的完整POWER帧均不能把同一次长按变成“解除再启动”；按键事件需要约180 ms静默间隔。

## 红1校色与视觉诊断

红1校色要求真实识别到唯一红1及其几何配对的蓝色参考条。连续三个当前配置的健康帧确认后，采集八个独立合格帧，并在后续SOF边界原子提交颜色阈值/配置版本。校色期间不允许运动；红2不能抢占校色。已经成功的校色不会因为红1一直留在画面里而反复执行；初始未校色流程可自动重试，显式重启可用下文的`calibrate --arm`。

默认分割最低值为红48、蓝20。校色由真实采样得到颜色最低值，不是自动调节所有识别参数：白色笔画最低值84、严格锚点白色门限及几何/数字检查仍属于固定算法参数。当前BCTL不提供任意红/蓝阈值写入。校色ACK只证明重新使能请求被接受，须通过`calibrated`、`calibrationSampleFrames=8`、配置版本及终态事件确认完成。

摆位时让卡牌完整入镜，保留背景余量并避免反光、明显模糊及大面积红色碎杂背景。颜色候选每色最多15个活动标签、共享16个完成候选；容量溢出会拒绝整帧。SW6能检查被拒绝候选的颜色、UNKNOWN及原因，SW7能检查中心局部RGB/HSV；局部采样不等于中心位置独立OCR。正常数字仍来自真实像素和每张卡的锚点/笔画，不从场景固定位置或候选索引推断。

## 三种模式

| 模式 | 感知来源 | 是否允许运动 |
|---|---|---|
| INTEGRATED，上电默认 | 真实相机和 B 算法 | 明确启动且真实安全条件满足时允许 |
| VISION_ONLY | 真实相机和 B 算法 | 始终零速；J3未连接也可选牌、追踪和校色 |
| CHASSIS_INJECT | FPGA按25 Hz生成的合成视觉报告 | 同一真实C控制器、IR/J3保护和UART；另外要求有效主机租约 |

切模式不启动任务，撤销旧授权并建立新请求/报告边界。真相机故障和校色状态继续保留；注入模式只隔离这些非活动来源条件，切回真实模式立即重新适用。IR和J3在两种可运动模式中始终有效。

上电、KEY0或切换模式时已经在画面里的红2不会启动；先移开红2并获得三个连续健康帧，再重新出示并连续确认三帧，才能产生一次新启动请求。STOP、急停、选择变化、原始相机模式和适用安全阻挡也撤销旧呈现；恢复后同样需要移开再出示。活动任务中红2不重置选择、任务或扫描预算。非活动任务重锁后最多等待1秒；未完成扫描标定时，必须等到新请求的目标完成三帧锁定才启动，已标定时可由健康无目标帧开始搜索。请让红2与所选蓝牌同时完整入镜；只展示红2而没有选定蓝牌，会等待超时并保持停车。STOP、IR、开关变化、模式切换、SW9、fatal或超声危险取消待启动操作。距离不安全时不接受红2启动；恢复后需移开并重新呈现，不会自行起步。

合法START还要求当前来源健康、距离有效且超声HOLD已解除。控制器不会保存一次不安全START，等待条件恢复后偷偷启动。JTAG START的事务ACK表示命令已解析，CLI随后检查控制器是否真的进入ARMED。

红2是START请求，不是“运行固定2秒再停车”的命令。正常任务根据视觉目标、安全条件、扫描预算及停靠状态推进。架空时轮转无法真实改变车体偏角或与目标的距离，不能用此条件要求完成落地DOCKED；目标移出后的停车与主机定时STOP也应分别观察。

## 可运行命令

从仓库根目录执行。使用Python 3.13。下方先指定本机实际可执行文件，避免系统默认Python 3.8或不可用的启动器；其他电脑修改该路径即可。工具自动查找Quartus；必要时在子命令前添加 `--quartus-bin C:\intelFPGA_lite\18.1\quartus\bin64`。指定目标时同时提供 `--cable` 和 `--device`。

```powershell
Set-Location 'C:\Quartus_Projects\ECHO72.0\github_publish\MTRX3700_MajorProject'
$pythonExe = 'C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe'
& $pythonExe tools/chassis_debug.py mode vision
& $pythonExe tools/chassis_debug.py status --watch

& $pythonExe tools/chassis_debug.py mode chassis
& $pythonExe tools/chassis_debug.py inject --x 80 --visible 1 --hold 3 --arm
& $pythonExe tools/chassis_debug.py scenario left-centre-right-loss --arm
& $pythonExe tools/chassis_debug.py scenario no-target-search --arm
& $pythonExe tools/chassis_debug.py scenario stale-frames --arm
& $pythonExe tools/chassis_debug.py stop

& $pythonExe tools/chassis_debug.py mode integrated
```

第一条`status --watch`会持续运行；按Ctrl+C退出观察会话后再继续下面的模式/注入命令。CLI子命令与参数以`--help`为准；没有独立的`chassis_debug.py start`子命令，真实整机通常用IR POWER或新呈现红2启动，注入通过`--arm`启动。

真实视觉状态、校色与抓帧可在没有其他JTAG会话时运行：

```powershell
& $pythonExe tools/echo7.py doctor
& $pythonExe tools/echo7.py status
& $pythonExe tools/echo7.py calibrate --arm
& $pythonExe tools/echo7.py capture --fresh
```

`echo7.py status`读取BCTL颜色/候选/报告状态；`chassis_debug.py status`读取CCTL选择/安全/任务状态。抓帧保留真实RGB565、结果字和CRC/版本检查，输出目录以本次命令记录为准。生产集成顶层由C独占SELECT/CLEAR；不要把旧B调试脚本中的`select/track/locate`当作实体拨码的替代入口，语音命令也不受支持。

需要保存连续观察时，使用`observe`。实体SW0–5仍决定目标；命令不会选择车位、改变模式、ARM、续租或STOP，只在一个持久会话内依次读取CCTL与BCTL。退出观察不会取消正在执行的INTEGRATED任务。先完成模式和实体开关设置，再运行：

```powershell
& $pythonExe tools/chassis_debug.py observe --samples 30 --out build/observations/bay1-normal1.json --label bay1-normal-trial1
# 或按时间观察；--seconds和--samples二选一。
& $pythonExe tools/chassis_debug.py observe --seconds 8 --out build/observations/bay1-window.json --label bay1-window
```

`--samples`计数的是轮询对，不保证每次都是新帧；`--interval`是每对读取之后的暂停，默认0.1秒。JSON保留所有坏帧、未锁定和重复样本，分别统计C/B不同帧数，并记录实体选择、模式、版本、阈值、请求tag及每次读取的开始/结束时间。CCTL与BCTL各自冻结，**不能把一对记录称为同帧快照**。`COMPLETE`只表示采集完成，不表示识别或运动验收通过；Ctrl+C或传输失败保留已读记录，BCTL失败时也保留该对已取得的CCTL。输出路径必须是新文件，不覆盖旧证据。

SW8静态视觉对照可先在VISION_ONLY进行。固定同一蓝牌、实体选择、相机位置/焦距、标牌摆位与光照，SW9保持关闭；正常模式SW8=0和旁路SW8=1各采集三次，每次使用相同`--samples`数。每次改用新的文件名和标签，例如`normal1.json`到`normal3.json`、`bypass1.json`到`bypass3.json`。改变SW8后先让当前请求/配置稳定；采集期间不要切牌、校色或换模式。随后离线比较：

```powershell
& $pythonExe tools/compare_observations.py --normal build/observations/normal1.json build/observations/normal2.json build/observations/normal3.json --bypass build/observations/bypass1.json build/observations/bypass2.json build/observations/bypass3.json --out build/observations/comparison.json
```

未提供`--conditions-confirmed`时，结果为`UNCONFIRMED_CONDITIONS`、退出码2。只有操作者确实核对这六次的相机、标牌与光照条件不变，才添加`--conditions-confirmed '如实填写本次条件确认'`。比较器核对六次的构建、算法/颜色配置、实体目标、运行模式和采样数，检查各次内部请求/config稳定及SW8取值；SW9原始画面、重复使用同次记录、时间顺序错误会被拒绝。`COMPARISON_VALID`只说明比较输入匹配，各模式的坏帧、丢锁和陈旧数据仍列出。结果同时给出全部轮询和不同帧统计；板上capture→completion时间不等于图像变化→UART或机械响应延迟。一个选定车位的静态三对比较也不等于六车位落地任务验收。

旧`echo7.py test --hardware [--trials N]`和`autodebug`依赖BCTL自动SELECT/CLEAR，与当前正式顶层的唯一请求所有者冲突，现明确返回`BLOCKED`、退出码2并指向`observe`。`autodebug`在构建、下载或板卡访问之前停止。历史B试验解析/评分保留用于读取旧证据，不能用旧命令声称当前自动测过六车位。

U坐标是旋转后画面的 `0..239`，V是 `0..319`；U=80/120/160分别表示左/中/右。`--hold` 单位为秒，默认3秒。不带 `--arm` 只更新模板，不能启动。模式切换、心跳和只读状态命令也不能启动。

持续注入在一个Quartus STP会话内更新模板、心跳和启动；正常退出或Ctrl+C时尽力STOP。主机异常退出后，FPGA约500 ms租约超时直接撤销注入许可；续租不会自动复驶。停止出帧但继续心跳，仍会被约150 ms报告新鲜度保护拦截。INTEGRATED不依赖JTAG心跳。

`scenario no-target-search --arm`读取当前FPGA的`scanBudgetUs`，保持合成无目标模板“预算秒数＋3秒”，覆盖最终零速报文、200 ms驻留、900 ms确认及轮询余量；默认10秒预算对应13秒会话。注入期间在同一会话持续输出CCTL状态并在分页间续租，可看到SEARCH、最终ACQUIRE、NOT_FOUND或真实HOLD。HOLD不累计搜索转动时间，因此会话时长不保证已完成预算；以保存的状态为准，退出仍尝试STOP。该命令没有设置扫描标定，也不把架空转动当作地面一圈。

**活动注入通过当前进程Ctrl+C停止。** 独立 `stop` 仅在JTAG链路空闲时使用；工具会拒绝争抢另一个底盘会话，打不开链路不等于STOP已送达。不要同时运行另一个BCTL/GRAB进程占用活动注入会话。

序列播放使用 `play <JSON文件> --arm`，文件为非空JSON对象数组，例如：

```json
[
  {"x": 80, "visible": true, "hold": 3},
  {"x": 120, "visible": true, "hold": 3},
  {"x": 160, "visible": true, "hold": 3},
  {"visible": false, "hold": 4}
]
```

每行还可设置 `y`、`quality` 或 `frames_enabled`。用户不需要维护内部tag、frameId或采集时间。模板先暂存后原子提交，未完成的事务不会成为半更新观测。CCTL采用稳定64位事务、toggle/ACK与错误码；STATUS冻结16字小快照，包含模式、开关、状态、请求/帧/配置、输入年龄、搜索预算、逻辑轮速、实际J3、IR及UART零速完成状态。

建议同时观察`mode`、`inputSource`、`selection`、`digit`、`requestTag`、`frameId`、`sourceHealthyFresh`、`targetObserved`、`targetLockedFresh`、`taskArmed`、`motionPermit`、`distanceValid`、`sonarHold`、`irEstop`、`failure`与`zeroSent`。命令ACK、读到新帧、目标锁定、任务授权和物理运动是不同事实；不能只用其中一个字段宣布整条链已通过。

## 搜索、对准、停车与恢复

`IDLE → SEARCH → ACQUIRE → ALIGN → APPROACH → DOCKED`，另有 `LOST`、`HOLD`、`NOT_FOUND`。未启动时只追踪。SEARCH仅在新鲜健康帧、真实安全保护和有效预算同时满足时以逻辑左右轮 `-4/+4 cm/s` 原地旋转；健康NOT_FOUND报告可以提供搜索活性，不要求目标锁定。

一帧身份、时间、配置正确且无歧义的目标便停止搜索。ACQUIRE先等完整零速度UART报文发送完，再等待默认200 ms保守驻留，最后建立新的采集边界。只有边界之后三个独立新帧并得到锁定结果，才允许对准/接近。确认窗口默认900 ms；这些等待参数尚不能冒充实测机械停稳时间。

ALIGN以4 cm/s等幅反向轮速转向，U在110–130为居中。APPROACH在500 mm以外用5 cm/s，350–500 mm用3 cm/s；目标仍对准、可靠且距离到350 mm时DOCKED。目标失效立即停止平移，先零速重获，再在剩余预算内搜索。DOCKED和NOT_FOUND撤销任务授权，距离或新图恢复不能重启；可以不全局复位而明确启动下一任务。

当前扫描采用**累计搜索转动命令时间**，没有已验证的真实航向反馈。只累计SEARCH获准转动的时间，ACQUIRE/HOLD停留不计入，另设120秒任务墙钟上限。方向查询接收链路保留，尚未据真实回包实现角度闭环。

默认10秒仅是未标定的有界底盘调试预算，状态为 `SCAN_UNCALIBRATED`。INTEGRATED未标定时禁止无目标正式扫描，已可靠可见目标仍可对准接近。要得到“标定后的近似360°扫描”，先在同一清空场地和固定轮速下做三次地面方向标记实测，记录转一圈用时与重复误差，再设置实际测得的时间：

```powershell
# 示例数字不是本工程的实测标定值。将30替换为三次实测选定值。
& $pythonExe tools/chassis_debug.py scan --seconds 30 --calibrated
```

`scan`修改会停车；`--calibrated`是操作者对真实测量的确认。标定状态保存在当前FPGA会话，KEY0/重新配置后失效。不能用仿真时间、架空轮转时间或任意秒数宣称地面360°已验收。扫描结束还会最终驻留确认，仍无目标则NOT_FOUND。

真实J3距离无效、无回波、过期或≤250 mm立即禁止运动并进入HOLD。恢复需三个**新的**有效测距样本且每次≥300 mm；不重复读取一个距离充数，不清除IR/fatal锁存，不刷新搜索总预算。正常350 mm停靠与250 mm保护停车分开报告。传感器每约100 ms测量，20–3999 mm为有效范围，有30 ms测量超时及1秒陈旧检查。

相机abandon、当前请求的坏帧或候选溢出立即停下并建立新边界，三个相邻、当前配置且新鲜的健康帧可恢复搜索资格，允许它们是NOT_FOUND。对准/接近仍必须重新三帧确认目标。候选溢出的历史诊断位保留，但画面恢复后无需全局复位；FIFO fatal、双bank耗尽等硬故障不随模式切换或好帧清除。若当前画面持续溢出，请让标牌完整入镜并简化背景，不能用复位代替画面纠正。

UART为115200、8N1、完整 `T:1` JSON，正常心跳200 ms；停车优先排在正在发送的完整JSON之后。默认两轮极性均为-1，逻辑正向5 cm/s实际发送 `{"T":1,"L":-0.05,"R":-0.05}`。物理转向与前进方向需架空确认，落地任务还要测实际停车误差。

## 三阶段操作

1. **VISION_ONLY**：实体SW0–5逐个选择六车位，SW6/7观察局部采样和拒绝原因；确认连续frameId、目标observed/locked、遮挡后丢失与重获。红1校色提交后重新确认；默认阈值也可调图和追踪，无须先完成校色。SW6每120个VGA帧自动换页（60 Hz时约2秒），第一页#0–7、第二页#8–F，页码与采样记录一起保持；编号是候选索引，旁边另列真实识别数字或UNKNOWN。中心RGB/HSV是局部采样，不是独立OCR，SW7仍在两页中连续可用。该阶段不用先使J3有效，轮端始终零速。
2. **CHASSIS_INJECT**：先使实际J3距离有效，架空检查U=80/120/160对应的轮向与前进极性。用真实反射板检查500/350/250 mm条件；验证无目标搜索、短暂目标出现、丢失、Ctrl+C/租约、IR A及两次新POWER。地面一圈标定只在可容纳整车旋转、四周清空且有真实有效回波的场地完成；单个前向J3不证明车身四周空旷。该阶段记录为合成视觉输入。
3. **INTEGRATED**：停止注入进程，模式切回integrated；实体开关选择，IR POWER或呈现红2启动。覆盖真实搜索→发现→驻留确认→对准→接近→停靠，六车位、丢失、障碍、无回波和急停分别记录。可断开电脑，正常任务不依赖主机续租。同场景下SW8正常/旁路各三次，记录真实任务时间、停车误差和画面变化到UART响应延迟。

目前速度下从1 m到350 mm仅理想行驶就约15秒，扫描和确认会增加时间。最终指标以本次实测冻结，不沿用旧proposal的12/18秒目标。

## 构建与验证

先确认Python路径与Quartus工具可用；如尚未安装工程Python依赖，可执行`& $pythonExe -m pip install -r requirements.txt`。依赖安装不属于R6计时。

```powershell
& $pythonExe tools/echo7.py build
& $pythonExe tools/echo7.py program
& $pythonExe tools/echo7.py test --rtl --only tb_control_repair tb_chassis_debug tb_pixel_uart_repair
```

也可在Quartus打开QPF执行Full Compilation；`quartus/output_files/PartBDebug.sof`是直接工程编译的默认位置。`echo7.py build`使用独立本次构建目录，实际SOF路径以成功记录为准。上面的`program`自动使用本机最近一次成功构建记录的SOF，也可用`--sof`显式提供该记录对应的绝对路径；它核对本次构建来源和产物，不能用旧SOF代表新功能。

发布文件使用固定路径：[E7070004 FPGA程序](firmware/E7070004/PartBDebug.sof)、[集成版数据表PDF](docs/ECHO7_Integrated_Datasheet.pdf)。本次004 SOF为**6706154字节**，来自已通过完整编译的004源码，不是003产物重命名。直接使用发布SOF时，在Quartus Programmer选择实际USB-Blaster和FPGA链位置2，添加该SOF并执行Program/Configure；本板下载后应由BCTL读回`buildId=0xE7070004`。链位置2是这块实际DE1-SoC的枚举结果，换板时先确认设备链。

预编译SOF不包含本机`echo7.py`成功构建记录，因此直接下载采用Quartus Programmer；`echo7.py program`仍只接受与本机成功构建记录相符的指定产物，不放松其来源保护。SOF配置是易失的；掉电后需重新配置，本文没有声称完成永久启动镜像部署。

发布数据表可由`docs/integrated_datasheet_metrics.json`中的记录重新生成，依赖为独立的文档工具依赖，不需要改动主视觉环境的`requirements.txt`：

```powershell
& $pythonExe -m pip install reportlab pypdf
& $pythonExe tools/render_integrated_datasheet.py
```

本机已有当前成功构建记录时，可导出整项目交接ZIP：

```powershell
& $pythonExe tools/export_submission.py --out build/echo7_submission.zip --datasheet docs/ECHO7_Integrated_Datasheet.pdf
```

导出核对当前源与成功构建，拒绝旧SOF或覆盖已有ZIP。包中仅有一份SOF，使用`firmware/<BUILD_ID>/PartBDebug.sof`，当前即`firmware/E7070004/PartBDebug.sof`，与README链接一致；不再另放`verified/PartBDebug.sof`副本。保留中英文README、工程/RTL/TB/工具、真实回放输入和文档；排除编译数据库、私有工具链与无关运行缓存。一页PDF不要求SHA sidecar，压缩包做CRC检查；对话记录只有显式指定已检查的导出manifest才会加入。新的克隆没有本机成功构建记录时，应先自行构建再运行导出器。ZIP完整性通过不增加任何实机验收结论，也不执行Git提交或上传。

| 已实际生成的版本 | 本次独立构建产物路径 | 构建状态 |
|---|---|---|
| E7070002 | `build/member_b/20261104T100141_653795Z_build/source/quartus/output_files/PartBDebug.sof` | PASS，已下载并记录该版硬件结果；历史产物不作为本次发布文件 |
| E7070003 | `build/member_b/20261104T104155_505074Z_build/source/quartus/output_files/PartBDebug.sof` | PASS，已下载；现场坏帧恢复已验证；历史产物 |
| E7070004 | `build/member_b/20261104T111202_124373Z_build/source/quartus/output_files/PartBDebug.sof`；发布副本`firmware/E7070004/PartBDebug.sof` | Full Compilation **PASS**；2026-11-04 22:31:50 AEDT实际下载且BCTL版本核对 **PASS**；红2重新选择/新锁/启动已观察，用户确认蓝1离开后实物停车 |

课程R6正式入口仍为 `./run_all_tests.sh`，要求clean copy、Verilator **5.050**、模块与系统自检、故意坏模块输出CAUGHT；本次用户目标为≤285秒（课程门槛300秒）。本机可用下列包装命令调用同一Bash入口，默认4任务编译；本轮完全相同的编译输入通过内部哈希缓存共享一次新编译，所有场景仍独立运行断言，不读取往轮二进制：

```powershell
& $pythonExe tools/run_r6_windows.py --compiler-bin 'C:\msys64\mingw64\bin' --bash 'C:\Program Files\Git\bin\bash.exe' --jobs 4
```

ModelSim通过不等于R6通过；各版规定环境内真实执行结果见验收记录。较完整历史视觉/Python回归按变更需要另跑，不用重复运行所有历史测试堆数量。

E7070004正式R6已在干净副本用Verilator5.050实际完成：**219.556074秒、退出0、12项及CAUGHT全部PASS、targetMet=true**，记录为`build/member_b/20261104T110801_416299Z_verilator_course/result.json`。此前E7070002为245.451876秒，E7070003为221.258456秒。加速来自同一次调用内按完全一致输入哈希共享新编译、独立continuous/overload场景并行及4任务编译；没有降低25fps输入速率、删除断言、force观察结果或复用上一轮二进制。故意坏模块仍必须由真实断言捕获。

`tb_control_repair`验证one-hot/模式/搜索/驻留/安全/负例及实际UART JSON；`tb_board_repair_pins`使用真实NEC脉冲、J3 TRIG/ECHO模型与115200 UART，无force控制器输入；像素系统链使用真实perceptionCore输入，合成视觉调试与真实相机回放各自明确标注。旧集成bench曾使用三位编码和锁死超声等旧语义，历史PASS不能沿用当前版本。

## 按版本区分的实机证据

以下路径是本次工作区的原始日志索引，`build/`中的完整编译数据库和仿真缓存不随仓库提交。可移植的结果叙述见[修复记录](docs/REPAIR_RESULT.md)，最终发布只保留当前SOF和数据表；不要把不存在于新克隆目录的本机日志误认为新的执行结果。

| 版本与输入层 | 已观察结果 | 证据索引与限制 |
|---|---|---|
| E7070002，合成视觉→真实底盘 | U80/U120/U160分别给出转向/同向前进/反向转向；停止心跳撤权且续租不自启；用户确认车轮运动及停车 | `build/repair/hardware_injection.jsonl`；`hardware_straight.jsonl`中用户确认两侧都向前；底盘架空 |
| E7070002，真实IR/J3/UART | A锁存急停，第一次POWER只解除，第二次新POWER启动；真实J3回波有效 | `build/repair/hardware_ir.jsonl`；不等于已实测全部距离边界与落地停车误差 |
| E7070002，真实画面摆位纠正 | 贴边裁切画面溢出；同张A4红1/蓝1移远后，24个不同帧中23次锁定，蓝1质量255，8帧校色得到41/24 | `build/repair/live_capture/`、`hardware_vision_e7070002.jsonl`；VISION_ONLY始终零速 |
| E7070003，真实坏帧恢复 | 历史faultFlags=3保留，frame338恢复`sourceHealthyFresh=true`和`targetLockedFresh=true`，同一运行未复位、未清故障 | `build/repair/hardware_recovery.jsonl`；证明修复E2永久阻断 |
| E7070003，真实连续视觉 | 23个不同帧中22次锁定；frame855蓝1质量255，U115/V186、122×130框、处理59.478ms | `build/repair/hardware_vision.jsonl`；VISION_ONLY零速，不称六车位落地完成 |
| E7070003，真实红2 | 请求tag5→6，重新选择生效；但启动早于新目标锁定，进入SCAN_UNCALIBRATED/NOT_FOUND，之后未自动复活 | `build/repair/hardware_red2_e7070003_early_start.jsonl`；明确记录失败，不作为红2成功验收 |
| E7070004，真实红2及真实相机 | tag3→4；frame2900先获得新锁，再ARM/ALIGN，逻辑L+4/R−4cm/s、真实J3=468mm；扫描未标定，failure=NONE，历史flags3保留；用户确认红2启动，随后澄清蓝1离开后即停车 | `build/repair/hardware_red2.jsonl`、`red2_console.log`；主机STOP记录的DISARMED、L0/R0、zeroSent=true证明板上状态/报文完成，其独立物理停车时刻未验；末状态VISION_ONLY、未ARM、逻辑零速，用户确认已停止 |
| E7070004，完整六张蓝牌真实视觉 | 同帧GRAB frame26844：蓝1–6均接受、质量255；另12个不同B帧中六张蓝牌分别12/12接受，C选蓝1为12/12健康/锁定，全部零速 | `build/continuation_20261104/six_cards_initial/`、`blue1.json`、`vision_findings.json`；红57/蓝37，配置1，正常透视；红2被绿色胶带遮住，拒识残余没有被伪造为有效数字 |
| E7070004，六档实体开关及非法选择 | 150.054秒、441对只读采样；六个one-hot均有对应蓝牌真实锁定，全零17次、冲突27次；全441次VISION_ONLY、未ARM、无运动许可、逻辑零速 | `build/continuation_20261104/six_switches.json`及`six_switches_analysis.json`；C健康390/441、锁定370/441，B好帧434/441；保留7个候选溢出坏帧及全部丢锁 |
| E7070004，SW6/7实物显示 | 用户确认SW6颜色信息可见；SW7中心位于白色空隙时显示局部颜色及“无标牌” | 见[修复记录](docs/REPAIR_RESULT.md)；尚未确认SW6两页/全部16槽/UNKNOWN/拒识原因，也未确认SW7中心覆盖标牌或歧义场景 |
| E7070004，合成视觉＋真实J3停靠 | 434个状态快照、78.931565秒；实际517mm时逻辑+5/+5，446mm时+3/+3，347mm首次DOCKED并撤权/零速；退远至534–615mm，2.194秒内12个快照仍DOCKED/零速 | `build/continuation_20261104/dock_hardware_01.jsonl`及`dock_analysis.json`；用户确认运动→减速→停止→退远不重启；底盘架空，不代表地面停靠误差 |
| E7070004，真实J3近停/滞回/恢复及独立STOP | HOLD03共469个状态快照、86.677721秒，6项条件PASS、该脚本无未验证项；近停、滞回仍停、退远恢复及随后STOP均获用户确认 | `build/continuation_20261104/hold_hardware_03.jsonl`及`hold_analysis_03.json`；合成视觉、真实IR/J3/UART、架空；本轮未观察轮向，未测机械停车延迟 |

E4触发后的约2秒继续读取状态而不发送心跳：13个采样均保持ARM且`leaseValid=0`，其中7个ALIGN、4个LOST、2个ACQUIRE。含触发采样共8个运动命令采样，**不能写成连续稳定转动2秒**；短暂视觉丢失时FPGA进入零速重确认。该次结束BCTL为frame2959、E7070004、好帧、蓝1质量255、U182/V130、101×117框、处理47.652ms，红2事件7/id2。此记录证明红2→新请求锁定→启动及INTEGRATED无需心跳；用户实物确认启动，并澄清“蓝一脱离后就停车了”。主机2秒STOP只独立确认板上撤销/zeroSent，其物理停车时刻未单独测量；不能把用户观察的停车归因于主机STOP或后续mode1切换。最终VISION_ONLY读回未ARM、逻辑零速，用户确认已停止。本轮不据此宣称六车位落地停靠或机械停车延迟已验收。

后续六档观察保留441个不同B帧和405个不同C缓存帧；C/B分别冻结，不要求每对同帧。主要蓝1–6区间的C锁定次数分别为197/200、22/23、24/28、16/22、23/29、26/30；另有一次未锁定的蓝2短过渡，冲突后返回蓝1为62/64。27次冲突中26次是持续稳定的mask3，另一次为mask6过渡；所有无选择/冲突样本均无C健康/锁定且B未选择目标。返回蓝1的首个样本保留旧CLEAR报告，C没有把它当作新锁。7个坏B帧均为candidateOverflow，之后均观察到好B帧；并非每个坏帧都在同一选择结束前观察到重新锁定。六档覆盖由此成立，但不是441次全时锁定或六车位落地通过。完整区间表和坏帧索引见[修复记录](docs/REPAIR_RESULT.md)。SW6/7目前只获得上表所列部分显示确认；SW8公平对照仍待实测。

J3续测使用合成视觉、真实测距/IR/UART和架空底盘。停靠记录中的517→446→347mm是首次状态变化的实测读数，不是尺子标定后的精确边界；条件确认点521/454/321mm是随后不同快照。首次DOCKED后83个快照、14.853秒内保持撤权/零速，包含反射板退远后2.194秒的确认窗口。用户确认这一实物过程；最终回到VISION_ONLY、IDLE、未ARM、零速。没有据此测得落地停车距离误差。

HOLD03的危险距离确认窗口为231–242mm、5个快照/0.647892秒；滞回窗口254–292mm、7个快照/1.163541秒均保持HOLD/零速。退远至367–407mm后，19个快照/3.119478秒观察到ALIGN及逻辑−4/+4。80.491761秒显式发送TX4 STOP，继续同一模板和心跳；STOP ACK至末样本6.093588秒内，34个不同帧的状态快照均未ARM、零速且zeroSent=true。其首末快照跨度为5.919557秒，原生frameId推进147；实际J3为367–376mm，租约、来源和目标锁定有效，无sonarHold/IR/fatal，模式、选择、tag和配置不变，之后才切到VISION_ONLY。用户确认“近停、滞回仍停、退远恢复、随后自动停”，未观察轮向。这里34次是状态轮询，不是34次独立测距；持续状态指全部记录样本，不测机械停车延迟，也不补证此前红2那次未隔离的STOP时刻。

前两次HOLD记录保留：HOLD01有362个快照/66.181秒，板上检查PASS，但用户未确认实物全过程并要求重做。HOLD02有434个快照/79.899秒，保留原FAIL；实测距离在滞回区间未连续保持主机要求的1秒便进入恢复范围，末状态已到313mm、ACQUIRE、仍ARM，主机却把阶段未完成当作失败立即STOP，截断恢复观察，用户因此未看到恢复。这不证明生产RTL恢复缺陷。一次性验收脚本已改为提前安全恢复时记录NOT_VERIFIED并继续、最终给PARTIAL；HOLD03完整满足各阶段，无跳过。生产恢复条件始终是连续三个新的有效测距≥300mm，1秒仅为本次滞回观测要求。脚本修复没有更改RTL/SOF；HOLD03清理正常。

构建资源/时序也按版本保留：E2为29417/32070 ALM，最差setup1.164ns、hold0.078ns；E3为29373/32070 ALM，最差setup0.967ns、hold0.117ns。两版M10K357/397、DSP51/87，未约束项0、四角及CDC检查通过。

**E4完整编译PASS**：1121.141秒，post-fit门检25.868秒，0 error、92 warnings；29576/32070 ALM（92%）、41000寄存器、M10K357/397、DSP51/87、2802640 memory bits、2个PLL。四角最差setup **+1.633ns**、hold **+0.118ns**，未约束项0；88项检查及每角63条同步链覆盖PASS，MTBF为NOT_ASSESSED。下载记录为`build/repair/program_e7070004_console.log`，板上BCTL已核对E7070004；硬件红2测试另行记录，编译/下载通过不替代运动验收。

## 已知限制与待完成测量

- 还没有完成六车位逐个落地闭环、三次地面一圈时间标定、350mm实际停车误差、完整任务时间及图像变化到UART响应延迟测量。不能把累计命令时间称为已验证的角度反馈，也不能把架空轮转称为地面360°。
- 实物J3近停、滞回、恢复和停靠状态已有上述架空证据；无回波实物验证、经尺子核定的250/300/350mm边界与绝对精度仍待完成，不能把报告读数直接当作真实几何距离。
- SW6两页、全部16槽、UNKNOWN和拒识原因，以及SW7中心覆盖标牌/歧义场景仍待实物确认；现有确认仅限SW6颜色信息和SW7白色空隙的颜色/“无标牌”。
- 还需SW8正常/旁路各三次公平实测，以及持续移动、遮挡、不同光照等更广场景。本轮保持适度验证，没有用重复长仿真替代实机。
- 复杂红色背景仍可能超出活动标签容量；当前坏帧停止授权，E3起可在新好帧后恢复，但持续坏图不会自动变成有效观测。裁切、反光、模糊和重复目标都可能被拒识。
- 历史frame251模型接受全部八张正式标牌；frame30321在原红41/蓝33配置下蓝6仍因颜色区域碎裂而几何拒识。一次保持原像素、只把蓝阈值降到20的离线对照恢复八牌接受；本次真实六牌在红57/蓝37下也全部接受。不同光照/阈值下的稳定性仍待验证，没有改历史输入或为数字6编造答案。
- E4红2实物启动和蓝1离开后停车已有用户确认，但视觉日志仍有LOST/ACQUIRE间歇，持续目标可见性需要改进。该次主机2秒STOP的独立物理时刻仍未测；后续HOLD03单独验证显式STOP后在持续输入/续租下不自启，并获得停车确认，但没有测机械停车延迟或本轮轮向。最终VISION_ONLY、未ARM、逻辑零速且实物已停，不扩大为落地停靠验收。
- A/C成员SID仍待本人补齐；原课程/IP声明和AI辅助改动说明保留，不虚构人工签核。

## 管脚与文件

| 接口 | FPGA信号 | 管脚 |
|---|---|---|
| 红外接收 | IRDA_RXD | PIN_AA30 |
| J3 TRIG / ECHO | GPIO_1[27] / GPIO_1[29] | PIN_AJ22 / PIN_AG22 |
| UGV02 UART TX / RX | GPIO_1[31] / GPIO_1[33] | PIN_AF23 / PIN_AD21 |

J3使用RCWL-1601、3.3 V和共地；FPGA TX接底盘RX，FPGA RX接底盘TX；没有新增J4传感器。相机/VGA管脚以QSF为准。B/C的24位请求、141位报告、76位状态和共享微秒时间均在CLOCK_50域，真实IR/J3始终位于合成视觉输入之外。

| 路径 | 用途 |
|---|---|
| `rtl/top/echo7IntegratedTop.sv` | 正式三模式顶层、真实/合成来源切换和板级连接 |
| `rtl/capture/`、`rtl/vision/`、`rtl/tracking/` | 相机传输、颜色/候选/投影识别和目标报告 |
| `rtl/interaction/` | 红1校色、红2新呈现确认及事件握手 |
| `rtl/member_c/` | 选择适配、任务状态机、IR/J3保护和UART底盘命令 |
| `rtl/debug/` | BCTL/CCTL、合成视觉、VGA采样诊断 |
| `tests/`、`run_all_tests.sh` | 模块/系统自检、真实输入fixture、正式R6入口 |
| `tools/chassis_debug.py`、`tools/echo7.py` | 持久JTAG会话、注入、构建、下载、校色及真实抓帧 |
| `tools/compare_observations.py`、`tools/export_submission.py` | 实体选择观测的三对SW8离线摘要、整项目单SOF交接ZIP |
| `firmware/E7070004/PartBDebug.sof` | 当前版本发布SOF；只在最终构建成功后发布 |
| `docs/ECHO7_Integrated_Datasheet.pdf` | 当前集成版数据表 |
| `docs/REPAIR_RESULT.md`、`VERSION_README.md`、`OWNERS.md` | 分版本结果、迭代记录及来源/成员归属 |

保留工程、RTL/TB、runner、真实相机输入/model/replay、最终SOF及报告所需测量值。编译数据库和仿真缓存不作为源码；不新增逐文件SHA清单或重复凭据包。原课程/IP声明保留；A/C成员SID待补，不虚构归属或人工签核。
