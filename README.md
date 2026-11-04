# ECHO-7 / MTRX3700：视觉引导车位搜索与停靠

[中文](README.md) | [English](README_EN.md)

正式工程是 `quartus/PartBDebug.qpf`，顶层是 `echo7IntegratedTop`，器件是 DE1-SoC 的 Cyclone V `5CSEMA5F31C6`。同一个 SOF 提供真实视觉调试、合成视觉底盘调试和整机运行。目标只能由实体 SW0–SW5 选择；JTAG 不提供直接轮速或假超声距离入口。

本次构建、下载和实机测试的具体结果见 [本次修复验收记录](docs/REPAIR_RESULT.md)。旧版本的拟合、仿真和实拍记录保留其历史含义，不代表当前代码已经完成实车验收。原始来源与成员归属见 [OWNERS.md](OWNERS.md)。麦克风和语音识别已取消。红1保留自动校色；按本次追加需求，红2在非活动任务时重新读取当前实体拨码、重锁并请求启动。

## 当前版本与验收范围

本次发布源码、成功构建SOF及实际下载读回均为 **E7070012**。E12新增ALIGN总时长和可关闭的起步段，默认20–100 ms、kick关闭；五项tune默认4/4/5/3/30保持。协议193检查/20报告、Python24项、Tcl模拟传输2项及控制44.0894113秒（两sign各2041检查/500UART，legacy848/289）通过，首次TB层次引用失败保留。正式R6首跑 **223.404755秒、13 PASS＋CAUGHT**；Full Compilation **1163.903秒**及post-fit **26.783秒PASS**，setup/hold +0.842/+0.102 ns，原始SOF6706156字节已实际下载。真实静止pulse读写、独立读回和参数隔离通过。地面前三轮INCOMPLETE；第四轮固定200 ms总时长进入APPROACH后由主机主动停车，用户接受轻微偏左，只证明有限回正。第五轮从已见目标接近仍 **INCOMPLETE，60.0399573秒**，反复对准后丢牌、重搜未找回，最终J3近障HOLD；收尾V1未ARM/零速/zeroSent、J3约254 mm，未DOCK。该五轮证据使用最后tune3/3/5/4/40、pulse200/200/60/6及15.1秒扫描；随后tol40→30另行实验尚待结果。所有实验参数均volatile、未写入SOF，也不是验证推荐；画外搜索停靠未通过。

历史已发布E11为 **E7070011**，该轮收尾VISION_ONLY、未ARM、零速；默认参数与当时最终实验配置分别记录。E11加入停车调参及失锁后完整停车重确认。控制定向runtime两sign各996检查/358完整UART、旧参数847/289通过；正式R6首轮302.015209秒超时FAIL保留，优化调度后的全新第二轮 **219.199994秒、13 PASS＋CAUGHT、targetMet=true**。Full Compilation1375.853秒＋post-fit26.278秒PASS，setup/hold +0.237/+0.120 ns，实际下载E11已核对。实板停车五项参数写入/独立读回、search改变使扫描标定失效及默认恢复均PASS；初始停车调参阶段未运动；后续已有真实地面试验，首轮与search3搜索均NOT_FOUND，turn3隔离仅抽动/INCOMPLETE。该轮只调参、不改E11 RTL；最终实验3/5/4/3/40、扫描15.1秒；turn5和approach4对照均INCOMPLETE，降速未解决抽动/过冲。本轮停止追加测试，组合仅作实验记录，不能称实测轮速或停靠通过。

历史E7070010已完成独立构建、下载及当时发布，实测收尾VISION_ONLY、未ARM、零速。用户接受较宽的居中范围后，本版默认改为U90–150（相对120为±30），并允许350 mm以外、已经新鲜锁定且U75–165的目标在START或完整ACQUIRE确认后直接进入APPROACH，减少不必要的停车原地对准。本版定向回归已PASS：默认正/负两sign各804检查/275UART、旧严格参数817/278，共29.1663517秒。正式R6已独立PASS271.31444秒、13 PASS＋CAUGHT，达到285秒目标；Full Compilation1260.493秒及post-fit25.832秒已独立PASS，setup/hold最差+0.909/+0.118 ns，实际下载和E10身份核对通过；蓝4零速校色预检4/4锁定。实机已从画外发现并锁定蓝4，短暂APPROACH后LOST并重启搜寻，最终 **NOT_FOUND/SCAN_BUDGET**；观察任务约22.21秒，未DOCK、未触发反向SEARCH。用户确认纸板固定、最后车轮停止；画外搜索停靠尚未通过。下面保留E9和更早版本的独立证据。

历史E7070009完成过构建、下载与发布，该版CCTL接口标识为 **E7070001**；E11现已改为真实BUILD_ID。E9两种TURN_SIGN各696检查/245条完整UART通过；正式R6独立 **PASS，274.530007秒、13项PASS＋CAUGHT、targetMet=true**。Full Compilation **1218.109秒**及post-fit门检 **26.779秒PASS**，ALM29699/32070（93%），最差setup **+0.629 ns**、hold **+0.117 ns**，未约束项0。原始E9 SOF已经实际下载并核对身份；下载后的蓝4居中预检4/4健康锁定、J3约663–664 mm、已校色且保持零速。E9画外蓝4实机为 **INCOMPLETE**：曾搜索到并锁定，随后反复对准，60秒观察窗内未停靠，主机STOP后回到VISION_ONLY零速；未发生反向SEARCH，本轮没有验证回扫物理效果。E9属于历史发布；构建与失败记录保留。

E8保留独立实物结果：蓝1、蓝3、蓝4从已见目标完成接近和停靠，首见ARM至DOCKED分别29.315066、15.726722、26.139371秒，终态J3分别329、321、316 mm。蓝1/4由一次主机START启动，蓝3由实体POWER启动；用户确认前进和停止，但蓝1/4末段微调约25/17秒，蓝4起步抽动、偏右及最终仍略偏右尚在。蓝2只有红2链路、窗口外人工前进反馈与事后终态的分段证据，没有完整运动日志。用户已取消蓝5/6单独地面任务；六牌静态覆盖不等于两牌地面任务通过。

E8最后的蓝4画外搜索扫过两次却未持续锁定，近距暂停、用户移障后恢复，最终耗尽13.6秒预算进入NOT_FOUND并自动停车。E9按用户要求增加看到目标后失去目标时的有限反向小步回扫；E8失败不回写为成功，E6时序失败与E5/E7实物失败也保留。迭代见[版本记录](VERSION_README.md)，详细命令、测量及证据见[修复记录](docs/REPAIR_RESULT.md)。

| 版本 | 该版关键变化 | 已取得的结果 |
|---|---|---|
| E7070002 | 三模式、实体独热选择、红2事件、完整安全链、分页视觉诊断 | Full Compilation和R6通过；实板注入、轮子运动、IR和真实蓝1追踪通过；之后发现单帧溢出历史位会永久阻断C |
| E7070003 | 将可恢复坏帧与历史故障位分离，接收时刻建立恢复边界 | 236项控制检查、R6和Full Compilation通过；实板保留faultFlags=3仍恢复健康锁定；23个真实不同帧中22次锁定；发现红2未标定启动过早 |
| E7070004 | 未扫描标定时，红2pending等待新请求的三帧目标锁定 | **254项定向检查PASS；正式R6 219.556074秒，12项及CAUGHT全部PASS；Full Compilation和实际下载PASS；用户实物确认红2启动、蓝1离开后停车**。主机2秒STOP的独立物理停车时刻未验证；末状态VISION_ONLY、未ARM、逻辑零速，用户确认已停止 |
| E7070005 | 生产转向符号−1；正常结束的超量程ECHO为FAR，异常信号仍保护 | **正式R6 239.403059秒，13项及CAUGHT全部PASS；Full Compilation及实际下载PASS**。零速蓝1健康锁定8/8；真实空旷FAR6/6且用户确认d页` FAr`。地面完整圈观察3/3，13.6秒近似扫描预算已写入，发布副本已复制 |
| E7070006，未下载历史版本 | 按U误差短促ALIGN及3/4 cm/s分档，停车后延长驻留并用新帧重确认 | 控制两种TURN_SIGN各338检查/53完整UART、14帧固定25fps像素→UART聚焦PASS；同次源码正式R6 **266.840318秒、13PASS＋CAUGHT**。首次Full Compilation因setup负裕量门检 **FAIL**，未下载/实机；1.5秒等待不是已测停稳时间 |
| E7070007，历史已下载版本 | 针对实际STA路径，将默认脉宽计算改为数值等价的窄位实现 | 默认256种U值一致、两种TURN_SIGN各338检查/53完整UART PASS；正式R6 **265.276162秒、13PASS＋CAUGHT**。Full Compilation/post-fit及实际下载读回PASS；真实蓝1第01–05轮未完成停靠，短促动作不对称/过冲仍在；连续直行隔离试验实际向前且基本直行 |
| E7070008，历史已验证版本 | 已处于APPROACH时，在U75–165内用同向5/3或4/3 cm/s连续纠偏；超出范围或近距未居中先完整停车、重确认再转向 | 两种TURN_SIGN各433检查/88完整UART PASS；正式R6 **270.641086秒、13PASS＋CAUGHT**，14帧像素→UART确认前进右纠偏3/5。Full Compilation/post-fit与实际下载读回PASS；零速蓝1预检4/4锁定。真实蓝1任务已记录板上DOCKED及零速驻留，用户确认持续前进、无明显偏转，探头前端终距约335 mm。蓝3实体POWER启动及真实接近/减速/微调/停靠已记录，用户确认稳定向前及约31 cm终距。蓝4从预锁定目标开始的真实接近与停靠已记录，起步抽动/偏右及末段修正耗时仍在；另一次画外搜索最终NOT_FOUND，未通过搜索闭环。蓝2另有红2链路及窗口外人工观察、事后终态，缺完整运动记录；用户取消本轮蓝5/6单测 |
| E7070009，历史已发布版本 | 正向SEARCH曾观察目标但停车确认超时且目标已离开时，有限反向小步回扫，每步后停车重确认 | 4 cm/s、150 ms、每任务最多3步，同一扫描预算与总任务计时；两种TURN_SIGN各696检查/245完整UART PASS；正式R6独立PASS274.530007秒、13PASS＋CAUGHT；Full Compilation1218.109秒＋post-fit26.779秒PASS，实际下载/身份读回PASS。画外搜索实机INCOMPLETE：发现/锁定后反复对准，60秒观察窗内未DOCK；主机STOP收尾，未触发反向SEARCH，回扫物理效果未验证 |
| E7070010，历史已发布版本 | 默认居中U90–150；>350 mm且新鲜锁定U75–165可在START/完整ACQUIRE后直接APPROACH | 定向PASS：默认两sign各804/275、旧严格参数817/278，29.1663517秒；正式R6独立PASS271.31444秒、13 PASS＋CAUGHT；Full Compilation1260.493秒＋post-fit25.832秒PASS；原始SOF6706157字节实际下载并核对E10。蓝4实机发现/锁定后短暂APPROACH，再LOST/SEARCH，22.2096082秒观察后NOT_FOUND/SCAN_BUDGET，未DOCK、无反向SEARCH，已零速收尾 |
| E7070011，当前已下载版本 | 停车V1五项调参；LOST必经完整ACQUIRE，确认义务跨HOLD/源失效 | runtime两sign各996/358、legacy847/289；首R6 FAIL302.015209保留，最终fresh R6 PASS219.199994秒/13 PASS＋CAUGHT。Full Compilation1375.853秒＋门检26.278秒PASS、实际下载和停车调参PASS；首轮/search3搜索NOT_FOUND，turn3/turn5均INCOMPLETE；最终3/5/4/3/40对照仍INCOMPLETE，降速未消除抽动/过冲；停止追加测试 |
| E7070012，当前发布 | ALIGN独立总时长与可关闭起步段，V1停车原子调参/独立读回 | 协议/控制/R6首跑223.404755秒/完整构建及实际下载PASS；真实静止调参PASS。前三轮INCOMPLETE，第四仅有限回正诊断通过用户观察，第五60.0399573秒INCOMPLETE/近障HOLD；未DOCK，实验tol30另行待验 |

已经完成真实硬件纠正及历史search4参数下塑胶地面的三次整圈观察，但六车位落地闭环和精确360°扫描尚未验收。早期实机主要在底盘架空条件下完成，后续地面记录另行标明；本README把现有实现、对应版本的实际证据和后续操作分别说明。后续复现实验的操作步骤也不代表已执行结果。

E5按新的实物反馈及用户要求，将生产`TURN_SIGN`改为−1，并把正常结束的超量程ECHO发布为FAR，保留信号异常保护。生产负号配置控制269检查、原12帧像素→UART及超声完整引脚专项46检查已分别通过。E5完整编译 **1173.143秒PASS**、post-fit门检 **25.799秒PASS**；最终R6 **239.403059秒PASS**，实际下载及E7070005读回通过。已取得的FAR/视觉零速实机结果与尚未完成的地面任务分别列出，首轮R6失败保留。

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
| SW6 | 候选信息及局部 RGB/HSV、颜色、数字和拒绝原因诊断；两页各8槽自动轮播，覆盖全部16候选 |
| SW7 | 中心白色8×8小框采样，以及覆盖该位置的完整识别牌身份 |
| SW8 | 轴对齐包围框识别 / perspective bypass；仍是同一相机画面和安全链，配置切换后重新确认观测 |
| SW9 | 去叠加的原始相机显示、暂停视觉处理；立即取消运动授权，关闭后仍需重新 START/POWER |
| IR POWER `0x12` | 无急停时启动满足条件的新任务；活动任务中不重置扫描预算 |
| IR A `0x0F` | 锁存急停，立即撤销运动许可 |
| 红1牌与配对蓝色参考条 | 自动建立颜色采样窗口，完成校色；参考条不是蓝色车位编号 |
| 红2牌 | 连续确认后，重新SELECT当前合法拨码；未标定时等待新目标三帧锁定再启动，VISION_ONLY只重锁 |
| 急停后的 POWER | 第一次新按压仅解除 IR 锁存，仍停车；松开后再次按压才能启动 |
| KEY0 | 全局复位；回到 INTEGRATED、DISARMED、零速，重新选择/校色及扫描标定状态 |
| KEY1 | HEX 距离 / NEC高16位 / NEC低16位分页，并保留相机快照功能 |

六位开关整体稳定约20 ms后建立选择。全0为 `NO_SELECTION`，多位1为 `SELECTION_CONFLICT`，均清除旧追踪且不能运动。合法选择未启动时也会真实追踪，便于独立调视觉；红2可以重新建立同一拨码的请求边界。运动中同步后的开关组合改变，先停车并取消旧任务，新选择还需新启动。

从左至右的六位数码管是 **HEX5页/选择状态、HEX4模式、HEX3–0数据**。HEX4显示模式：`0` INTEGRATED、`1` VISION_ONLY、`2` CHASSIS_INJECT，**不是车位编号**。HEX5在稳定后的全0选择时显示 `n`，稳定多选冲突时显示 `C`，有效单选才显示当前距离页 `d` 或 NEC 页 `H/L`。`n/C`只覆盖页字符，模式和右侧数据仍按当前页显示；约20 ms去抖期间不能只凭页字符判断开关是否已经稳定。HEX3–0显示毫米距离或对应NEC数据，无效距离留空；E5新增确认远距时显示` FAr`。完整任务状态、选定编号和故障原因通过 `chassis_debug.py status` 读取。

读距离时只看`d`页右侧四位HEX3–HEX0，普通数值为**十进制毫米**。例如`d2 0520`表示距离520 mm（52.0 cm），左侧`d2`是“距离页＋CHASSIS_INJECT模式”，不能一起当成距离数字。E5的` FAr`表示确认超量程/正常无反射的远距状态，内部编码`distance_mm=4000 && distance_valid=true`，**不是测得4米**。CLI提供`distanceKind=MEASURED/FAR/INVALID`及`distanceFar`；旧E4的`4000,false`仍为INVALID。按KEY1在`d → H → L`之间换页；H/L右四位是遥控NEC码的十六进制数据，不是测距值。距离无效时右四位全部熄灭，不应把空白读成0 mm。

H页是最近一次有效完整NEC码的高16位，右两位才是命令字节：POWER为`12`，A为`0F`，对应示例为`H0 ED12`和`H0 F00F`。L页是同一码的低16位地址数据；尚未收到有效完整码时，H/L数据为空白。这是最近收到的按键码，不是当前急停锁存状态，也不是左右轮速度。KEY1每次松开后重新按下翻一页，长按不会连续翻页；其快照功能不会冻结VGA画面或切换运行模式。

显示、控制器和JTAG状态使用同一份超声`distance_mm`，传感器约每100 ms产生一次新测量；JTAG读取时刻不同，快照可能与眼前显示相差一次更新。毫米是代码定义的单位，尚不保证与尺子的绝对精度一致。现场调整反射板摆位后读数曾从379 mm变为520/521 mm，反射面和尺子测量起点尚未核定；不能据此修改换算系数或宣称已完成距离标定。

LEDR0非零运动许可，1 IR急停锁存，2距离有效（包括FAr），3已停靠，4当前超声停止原因（IR优先），5 UART忙，6/7 NEC完整帧/重复帧脉冲，8已确认且新鲜的运动目标，9未授权且距离有效。LED0不是ARM状态，LED9也不是全系统READY；它没有检查全部视觉、选择和IR条件。`LEDR0=0`、零速JSON已经发完、车体物理停稳是三件不同的事。NEC重复帧和连续重发的完整POWER帧均不能把同一次长按变成“解除再启动”；按键事件需要约180 ms静默间隔。

## 红1校色与视觉诊断

红1校色要求真实识别到唯一红1及其几何配对的蓝色参考条。连续三个当前配置的健康帧确认后，采集八个独立合格帧，并在后续SOF边界原子提交颜色阈值/配置版本。校色期间不允许运动；红2不能抢占校色。已经成功的校色不会因为红1一直留在画面里而反复执行；初始未校色流程可自动重试，显式重启可用下文的`calibrate --arm`。

默认分割最低值为红48、蓝20。校色由真实采样得到颜色最低值，不是自动调节所有识别参数：白色笔画最低值84、严格锚点白色门限及几何/数字检查仍属于固定算法参数。当前BCTL不提供任意红/蓝阈值写入。校色ACK只证明重新使能请求被接受，须通过`calibrated`、`calibrationSampleFrames=8`、配置版本及终态事件确认完成。

摆位时让卡牌完整入镜，保留背景余量并避免反光、明显模糊及大面积红色碎杂背景。颜色候选每色最多15个活动标签、共享16个完成候选；容量溢出会拒绝整帧。SW6能检查被拒绝候选的颜色、UNKNOWN及原因，SW7能检查中心局部RGB/HSV；局部采样不等于中心位置独立OCR。正常数字仍来自真实像素和每张卡的锚点/笔画，不从场景固定位置或候选索引推断。

### VGA画面怎么读

正常画面中央是竖向相机图像，叠加红/蓝颜色轮廓。接受的牌显示白字标签：红底`R1/R2`、蓝底`B1–B6`，配对蓝参考条显示`BJ`。这些是识别身份，不能把标签或颜色轮廓当作车辆已启动或目标已完成控制锁定；当前画面没有常驻的大检测矩形、绿色锁定框或`MODE/ARM/selected/LOCK`文字行。

| 画面内容 | 使用含义 |
|---|---|
| `CAL:W / B / Y` | 待校色 / 正在校色 / 已校色；校色时保持牌和相机稳定 |
| `CFG`、`SAMPLE` | 当前颜色配置及校色采样进度，供检查是否实际完成校色 |
| `FRAME:GOOD / BAD / STALE`、`VGA/META`帧号 | 图像元数据的好帧/坏帧/新鲜度与帧关联诊断；GOOD不等于已经ARM |
| `RED2:RESELECT` | 固定功能提示，不是“刚刚触发了红2”的事件灯 |
| `STATE` | B侧校色/交互状态，不是SEARCH、ALIGN或DOCKED导航状态 |
| SW6、`PAGE:1 / 2` | 约2秒换页：第1页槽0–7，第2页槽8–F；候选颜色、牌号或UNKNOWN、REF、拒识码E及RGB/HSV。黄色小采样标记与槽号关联 |
| SW7、`CENTRE8X8` | 中心白色8×8框的局部颜色、RGB/HSV和覆盖中心的完整牌身份；无牌或歧义会明确显示 |
| SW8、`BYPASS:1` | 改用轴对齐包围框识别作为算法对照；仍显示同一相机画面，不显示一幅拉正后的图，也不绕过IR/J3保护 |
| SW9 | 去掉诊断叠加的相机画面，保留既有竖向显示方向；退出后需要新的启动操作 |

红、蓝牌作用不同：蓝1–6是可选停靠目标，蓝参考条只参与红1校色，红2只发重新选择/启动请求。出示红2时把它放在目标旁边，避免遮住蓝牌、遮挡J3或把手放得比目标更近；近处反射物可能使车辆保护停车或提前满足停靠距离。

## 三种模式

| 模式 | 感知来源 | 是否允许运动 |
|---|---|---|
| INTEGRATED，上电默认 | 真实相机和 B 算法 | 明确启动且真实安全条件满足时允许 |
| VISION_ONLY | 真实相机和 B 算法 | 始终零速；J3未连接也可选牌、追踪和校色 |
| CHASSIS_INJECT | FPGA按25 Hz生成的合成视觉报告 | 同一真实C控制器、IR/J3保护和UART；另外要求有效主机租约 |

切模式不启动任务，撤销旧授权并建立新请求/报告边界。真相机故障和校色状态继续保留；注入模式只隔离这些非活动来源条件，切回真实模式立即重新适用。IR和J3在两种可运动模式中始终有效。

上电、KEY0或切换模式后，红2首先处于禁止重触发状态；先移开红2，使算法连续三个健康帧判定红2缺席，再重新出示并连续确认三个健康帧中唯一有效的红2，才能产生一次新启动请求。这是识别结果的缺席/出现边界：实物仍留在画面但连续漏识三帧，也可能重新满足重触发条件。STOP、急停、选择变化、原始相机模式和适用安全阻挡也撤销旧呈现；恢复后同样需要上述新边界。活动任务中红2不重置选择、任务或扫描预算。非活动任务重锁后最多等待1秒；未完成扫描标定时，必须等到新请求的目标完成三帧锁定才启动，已标定时可由健康无目标帧开始搜索。未标定时应让红2与所选蓝牌同时完整入镜；只展示红2而没有选定蓝牌，会等待超时并保持停车。STOP、IR、开关变化、模式切换、SW9、fatal或超声危险取消待启动操作。距离不安全时不接受红2启动；恢复本身不会保留并重放旧启动请求。

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

`scenario no-target-search --arm`读取当前FPGA的`scanBudgetUs`，保持合成无目标模板“预算秒数＋3秒”；E5按最终零速报文、200 ms驻留、900 ms确认及轮询余量执行，默认10秒预算对应13秒会话。E7及E8使用1.5秒驻留，不能仅据主机会话时长判定任务完成。注入期间在同一会话持续输出CCTL状态并在分页间续租，可看到SEARCH、最终ACQUIRE、NOT_FOUND或真实HOLD。HOLD不累计搜索转动时间，因此会话时长不保证已完成预算；以保存的状态为准，退出仍尝试STOP。该命令没有设置扫描标定，也不把架空转动当作地面一圈。

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

## E11：停车状态下的小范围调参

此五项调参从E11加入，E12继续支持；旧版E10没有调参能力，配套新工具读取旧板时会拒绝写入，不会把旧状态字当作新调参寄存器。`tune`无参数只读状态，查看`tuningSupported`与`tuning`；指定任意字段时，先读当前五项、合并本次修改，再一次原子写入整组并读回核对。所有值必须是表内整数，且`approach > fine`。这些是控制器的逻辑cm/s请求与像素容差，不是电机PWM、实测轮速或遥控车轮接口。

**固件默认与当前实验不同：**复位默认4/4/5/3/30；历史E11测试收尾为3/5/4/3/40、扫描15.1秒。参数不会写回SOF；turn5已完成但仍INCOMPLETE，approach4对照也已INCOMPLETE，当前组合属于实验记录，不是验证推荐。

| CLI字段 | 范围 / 默认值 | 作用 |
|---|---|---|
| `--search` | 3–5 cm/s / 4 | 正常SEARCH及有限反向SEARCH的等幅转动请求；改变会使扫描时间标定失效 |
| `--turn` | 3–5 cm/s / 4 | 大误差ALIGN短转速度；误差≤30且仍在容差带外的细转保留固定3 cm/s |
| `--approach` | 4–8 cm/s / 5 | >500 mm时的居中前进速度与差速快轮；必须大于fine |
| `--fine` | 3–4 cm/s / 3 | 350–500 mm居中前进速度及差速慢轮；近距差速快轮为fine+1 |
| `--tolerance` | 10–40像素 / 30 | U120两侧可接受居中范围，默认U90–150；也用于停靠居中判定 |

写入必须已处于 **VISION_ONLY、未ARM、无运动许可、左右命令均0且zeroSent=true**。CLI不会自动STOP、切模式、ARM、续租或启动；FPGA也独立检查停车条件。操作时先明确停车并切VISION_ONLY，再确认实物停稳和状态。例子中的读写命令只改参数，不会自动开始任务：

```powershell
& $pythonExe tools/chassis_debug.py tune
& $pythonExe tools/chassis_debug.py mode vision
& $pythonExe tools/chassis_debug.py status
& $pythonExe tools/chassis_debug.py tune --turn 4 --tolerance 30
& $pythonExe tools/chassis_debug.py tune --defaults
```

`--defaults`一次恢复`search/turn/approach/fine/tolerance = 4/4/5/3/30`，不能与单项选项混用。写后返回状态中的五项必须与期望相同；读回不匹配属于未确认，不是已生效。参数仅保存在当前FPGA会话，KEY0、掉电或重新下载后恢复默认，不写入永久存储。

**只要search值发生变化（包括恢复默认时改变search），scanCalibrated便清除。** 新速度不能沿用或按比例换算旧13.6秒；须在实际场地和当前速度重新验证地面扫描用时后再设置`scan --seconds ... --calibrated`。恢复到已有实测记录的原速度时，也须确认场地/配置仍适用并显式恢复该记录，默认恢复本身不恢复标定。修改其余四项保留扫描标定；改变场地、供电、轮胎等实际条件仍需重新评估适用性。调参不提供修改250/300/350/500 mm距离边界、IR急停、视觉时效/三帧资格、1.5秒驻留或120秒任务上限的入口。

传输使用CCTL opcode11单个32位配置字，STATUS word13以高字节`0xA1`声明能力、低22位读回五项。E11顶层传入实际设计ID，Tcl改为接受E707设计族，同时严格保留CCTL magic、协议meta和16字数量检查；旧版无A1能力则`tuningSupported=false`，写操作在发送前拒绝。身份兼容检查放宽到设计族不等于绕过协议或给旧固件增加调参能力。 E11必须配套新版`tools/tcl/chassis_session.tcl`；旧主机硬编码E7070001，会拒绝新的实板身份。新主机可读取旧E707板卡，但没有A1能力就不能写调参。

## E12：独立设置ALIGN总时长与起步段

E11的低速短转在地面上出现只抽动、单侧起转及过冲，降低前进请求也未解决。E12因此加入独立的`pulse`配置，供实机逐项比较；它只影响需要原地对准的**ALIGN**，不改变SEARCH（含反向回扫）或APPROACH，不自动启动任务。允许设置的范围是接口边界，不是已验证的机械工作范围。

| CLI字段 / 状态字段 | 范围、步长 / 默认 | 含义 |
|---|---|---|
| `--min-ms` / `minMs` | 20–300 ms，10 ms / 20 | 一次ALIGN总请求时长的下限 |
| `--max-ms` / `maxMs` | 20–300 ms，10 ms / 100 | 一次ALIGN总请求时长的上限，必须≥minMs |
| `--kick-ms` / `kickMs` | 0–100 ms，10 ms / 0 | 起步段时长；0关闭；受本次总时长截断 |
| `--kick-speed` / `kickSpeed` | 3–8 cm/s，整数 / 5 | 向UGV02发出的UART速度请求幅值，不是实测轮速、PWM、电流或转矩 |

需要ALIGN时，原误差规则按`2 ms × abs(U−120)`选择总时长，再夹在minMs/maxMs之间；已在容差带内则不创建短转。**总时长包含kick，不是“总时长再加kick”。** 进入ALIGN时锁存总时长及两个速度：先用kickSpeed持续`min(kickMs, 本次总时长)`，剩余时间沿原方向使用`tune --turn`（3–5 cm/s）；小误差且仍在较窄容差带外时，后段仍固定3 cm/s。例如总时长40 ms、kickMs60，只能执行最多40 ms起步段，没有额外慢速段；这只是逻辑例子。速度分档不强制kick高于后段，默认kickMs=0时kickSpeed不参与运动，20/100/0/5默认保留E11的短转行为。

`pulse`无参数只读`alignTimingSupported`和`alignTiming`。指定任意字段时，主机读取当前四项、合并本次改动，再用一次原子写入提交整组，随后独立读取状态核对四项完全相同；`--defaults`恢复20/100/0/5，不能与单项选项混用。写入仅允许**VISION_ONLY、未ARM、无motionPermit、左右逻辑命令0、zeroSent=true**；CLI不替用户切模式、START、ARM或续租，FPGA也独立拒绝不满足停车边界或非法范围的写入。

```powershell
# 读取能力与四项当前值；不续租、不启动
& $pythonExe tools/chassis_debug.py pulse
# 仅在已停车VISION_ONLY并核对状态后写入；下例与默认相同
& $pythonExe tools/chassis_debug.py pulse --min-ms 20 --max-ms 100 --kick-ms 0 --kick-speed 5
& $pythonExe tools/chassis_debug.py pulse --defaults
```

minMs是**计算名义总时长**的下限，不是必须持续运动的最短时间；目标进入容差带/跨方向、丢牌、IR或J3保护均可能提前停车，使实际请求短于minMs。kickSpeed通过UGV02 UART发送速度请求，是否克服静摩擦、两轮是否同时起转及实际速度仍须实机确认。

此配置与E11五项`tune`独立：`pulse --defaults`不改search/turn/approach/fine/tolerance，`tune --defaults`也不恢复pulse。只修改pulse不清扫描标定，主机同时核对scanCalibrated、scanBudgetUs和五项tune保持不变；若修改search，仍按原规则清标定。两组参数均为volatile，KEY0、掉电、重新下载恢复各自默认，扫描标定需重新核对。修改pulse不开放250/300/350/500 mm距离边界、IR保护、视觉时效、停车驻留和任务总限时；短转到限、目标进入容差带、跨方向或保护中断仍按既有规则停车、重确认，不承诺机械停稳时间。

协议使用独立**CCTL opcode12**，单次32位写入中只有低18位有效；时间以10 ms单位编码，高位必须0。STATUS **word15 bits27:20为0xA2**，bits19:2回读四项，bits1:0仍是模式，高四位原lease/template/scan/frames标志保持。原opcode11及word13的A1五项调参接口不变。旧E11板无A2时`alignTimingSupported=false`，主机在发送前拒绝pulse写入，仍可正常读取或使用其已有tune能力；必须使用配套E12主机/Tcl，不能把旧状态字误认成pulse配置。

当前接口及主控制定向仿真/主机测试已有通过证据。零速实板写入和独立读回已通过；实际短转速度阶段、轮子同步起转、过冲改善与搜索停靠结果仍待记录，不能由参数读回或计时逻辑推断。

## 搜索、对准、停车与恢复

`IDLE → SEARCH → ACQUIRE → ALIGN → APPROACH → DOCKED`，另有 `LOST`、`HOLD`、`NOT_FOUND`。未启动时只追踪。E5生产参数`TURN_SIGN=-1`，SEARCH仅在新鲜健康帧、真实安全保护和有效预算同时满足时以逻辑左右轮 `+4/-4 cm/s` 原地旋转；健康NOT_FOUND报告可以提供搜索活性，不要求目标锁定。E4旧方向为−4/+4，其历史记录保留。

一帧身份、时间、配置正确且无歧义的目标便停止搜索。E5的ACQUIRE先等完整零速度UART报文发送完，再驻留200 ms，最后建立新的采集边界。只有边界之后三个独立新帧并得到锁定结果，才允许对准/接近。确认窗口默认900 ms。实机短转表明200 ms之后画面位置仍在变化，不能把zeroSent或驻留结束等同机械停稳；E6已将板级默认驻留改为1.5秒，聚焦逻辑仿真通过，实物停稳仍待验证。

E5的ALIGN以4 cm/s等幅反向轮速持续纠偏，U在110–130为居中。APPROACH在500 mm以外用5 cm/s，350–500 mm用3 cm/s；目标仍对准、可靠且距离到350 mm时DOCKED。目标失效立即停止平移，先零速重获，再在剩余预算内搜索。DOCKED和NOT_FOUND撤销任务授权，距离或新图恢复不能重启；可以不全局复位而明确启动下一任务。

E6引入、E7实际下载的ALIGN会在进入时一次锁定方向、速度和脉宽：时长按`abs(U−120) × 2000 µs`计算并限制在20–100 ms；误差>30像素时4 cm/s，误差≤30且在居中死区外时3 cm/s。达到时限、转入居中区或误差跨方向时先停车，复用ACQUIRE，默认等待1.5秒后建立新边界，取得三个新帧才再次决定转动或前进。SEARCH保持4 cm/s，IR/J3保护和FAR语义保持原设计。逻辑仿真已通过，但E7实车仍出现单侧短促动作和跨中心：1.5秒不是已测机械停稳上界，短脉冲未证明消除过冲，3 cm/s也未证明能可靠同步起转。

E7仅修改`motion_fsm`的默认脉宽算术路径：8位绝对误差先截限到10–50（6位），再用17位移位/减法得到原脉宽。默认配置的全部256种U输入逐一数值一致，非默认配置保留完整通用回退计算；速度档位、脉宽范围、SEARCH、驻留、采集边界和保护参数均不改变。聚焦控制回归、E7正式R6及完整post-fit时序均已通过，固件已下载；该时序修正没有消除后续真实任务记录中的运动问题。

E8只在**已经进入APPROACH**、目标仍健康锁定且距离>350 mm时增加连续前进纠偏。U110–130仍为居中，维持原5/5（>500 mm）或3/3（350–500 mm）；U75–109或131–165则命令两轮均向前，远距用5/3、近距用4/3 cm/s，快轮命令按目标方向选择。生产负转向符号下，低U为逻辑左轮较快、高U为逻辑右轮较快。超出U75–165，或距离≤350 mm但未居中，立即撤销前进，进入ACQUIRE；完整零速UART完成后等1.5秒、建立新采集边界并确认三个新帧，才决定是否ALIGN，避免前进后立即反转一侧轮。既有安全条件满足、居中且距离≤350 mm才DOCKED。START、SEARCH、原ALIGN脉冲和IR/J3/FAR保护不变；该功能已通过聚焦控制、正式R6及Full Compilation/post-fit，并已下载；真实闭环结果仍需单独确认。

E9只由**正常正向SEARCH中的目标observed**触发ACQUIRE时授予回扫资格。确认超时且目标已经离开，才反向4 cm/s回扫150 ms；每任务最多3步，复用SEARCH状态但改变方向。获准的反向逻辑转动时间同样计入`scanElapsedUs`，沿用任务总预算和`taskStart`，不重新计时。每步后等完整零速UART，再等1.5秒、建立新采集边界，要求三个新帧确认目标。锁定成功、源失效、HOLD或取消清除授权，HOLD不会补回已用次数；没有先看到目标的普通空场搜索不触发回扫。其他ALIGN/APPROACH、安全与FAR行为沿用E8。该实现和TB已冻结，定向控制、正式R6、Full Compilation/post-fit及下载身份读回均已通过；画外搜索实机已记录INCOMPLETE：发现/锁定后对准反复，60秒观察窗未DOCK，主机STOP正常收尾；未触发反向SEARCH，回扫物理效果未验证。

历史search4的13.6秒来自**连续正向扫描**的三次实物圈观察。E9反向回扫也消耗同一总预算，净正向扫角会更小；它仍是有界运动时间，不是精确360°，原圈数据不能保证开启回扫后覆盖整圈。E9当时恢复了该13.6秒记录；E11后期改search3并基于两次单圈与一次双圈参考设置15.1秒；E12首轮准备沿用该速度/同场地基准，证据另列，不能继续把13.6秒称作当前实验预算。

E5对准时U<110给逻辑`+4/-4`，U>130给`-4/+4`。B端固定坐标为`U=floor((native yMin+yMax)/2)`、`V=floor((638-native xMin-native xMax)/2)`；VGA经过90°旋转后，屏幕左右对应U，非V，`orientationProfile`只影响字形/anchor读取。实物静态检查已确认车体前左蓝1约U80、前右约U174而V约158稳定；E4的−4/+4曾实际俯视顺时针，故E5修正转向符号。E5首圈已由用户确认逻辑+4/−4实际逆时针，证明实物转向纠正；仍未独立确定底层P1/P2物理线序原因，真实目标对准闭环需另验，B坐标未改。

当前扫描采用**累计搜索转动命令时间**，没有已验证的真实航向反馈。只累计SEARCH获准转动的时间，ACQUIRE/HOLD停留不计入，另设120秒任务墙钟上限。方向查询接收链路保留，尚未据真实回包实现角度闭环。

默认10秒仅是未标定的有界底盘调试预算，状态为 `SCAN_UNCALIBRATED`。INTEGRATED未标定时禁止无目标正式扫描，已可靠可见目标仍可对准接近。要得到“标定后的近似360°扫描”，先在同一清空场地和固定轮速下做三次地面方向标记实测，记录转一圈用时与重复误差，再设置实际测得的时间：

```powershell
# 仅适用本轮search3/塑胶地面：两次单圈+一次双圈参考得到15.1秒，并非三次精确单圈。
& $pythonExe tools/chassis_debug.py scan --seconds 15.1 --calibrated
```

`scan`修改会停车；`--calibrated`是操作者对实际测量条件的确认。上例仅对应本轮search3、同一塑胶地面的15.1秒实验预算（`scanBudgetUs=15100000`），依据为两次单圈14.093147/14.691960秒及一次双圈30.014554秒参考，不能称三次精确单圈或精准360°。旧search4的13.6秒保留历史范围。预算和调参都在当前FPGA会话，KEY0/重新配置后失效；恢复时须重新核对速度、场地、供电和已有记录，不盲目复制。反向回扫消耗同一预算，实验室环氧地面未测；最终驻留后无目标仍NOT_FOUND。

用户后续明确要求正常空旷/无反射按障碍很远处理。E5区分三类J3结果：20–3999 mm为实际测距；本次确有TRIG、脉冲达到驱动约23.3 ms量程上限且ECHO在事务80 ms期限前真实回低时，发布`4000,true`的FAR哨兵；没有上升沿、预先高电平导致未触发、期限内仍卡高、非法短脉冲<20 mm或接收数据过期仍为INVALID。FAR不靠时间一到就伪造，也不把39 ms写死为唯一正常长度；专项覆盖24/39/75 ms已结束脉冲。

真实INVALID/过期或有效测距≤250 mm立即禁止运动并进入HOLD，IR保护保留。恢复仍需三个**新的**有效且≥300的测距/确认FAR样本；不重复读取一个距离充数，不清除IR/fatal锁存，不刷新搜索总预算。正常350 mm停靠与250 mm保护停车分开报告。触发周期仍约100 ms、接收端陈旧上限仍1秒；E5本事务响应期限由E4的30 ms延至80 ms，给正常长脉冲回落留下有界等待并在下次触发前保留约20 ms。超过该界限仍按异常处理，不能推断任意长的高电平都是空旷。

相机abandon、当前请求的坏帧或候选溢出立即停下并建立新边界，三个相邻、当前配置且新鲜的健康帧可恢复搜索资格，允许它们是NOT_FOUND。对准/接近仍必须重新三帧确认目标。候选溢出的历史诊断位保留，但画面恢复后无需全局复位；FIFO fatal、双bank耗尽等硬故障不随模式切换或好帧清除。若当前画面持续溢出，请让标牌完整入镜并简化背景，不能用复位代替画面纠正。

UART为115200、8N1、完整 `T:1` JSON，正常心跳200 ms；停车优先排在正在发送的完整JSON之后。默认两轮极性均为-1，逻辑正向5 cm/s实际发送 `{"T":1,"L":-0.05,"R":-0.05}`。物理转向与前进方向需架空确认，落地任务还要测实际停车误差。

## 三阶段操作

用户已确认蓝1–6和红色功能牌均为独立打印，可分别移动；这为逐车位摆位提供了条件，尚未完成六个实际地面任务，不能把打印准备记为闭环通过。

1. **VISION_ONLY**：实体SW0–5逐个选择六车位，SW6/7观察局部采样和拒绝原因；确认连续frameId、目标observed/locked、遮挡后丢失与重获。红1校色提交后重新确认；默认阈值也可调图和追踪，无须先完成校色。SW6每120个VGA帧自动换页（60 Hz时约2秒），第一页#0–7、第二页#8–F，页码与采样记录一起保持；编号是候选索引，旁边另列真实识别数字或UNKNOWN。中心RGB/HSV是局部采样，不是独立OCR，SW7仍在两页中连续可用。该阶段不用先使J3有效，轮端始终零速。
2. **CHASSIS_INJECT**：先使实际J3读数有效（E5允许确认FAR），架空检查U=80/120/160对应的轮向与前进极性。用真实反射板检查500/350/250 mm条件；验证无目标搜索、短暂目标出现、丢失、Ctrl+C/租约、IR A及两次新POWER。地面一圈标定只在可容纳整车旋转、四周清空且J3正常工作的场地完成；单个前向J3不证明车身四周空旷。该阶段记录为合成视觉输入。
3. **INTEGRATED**：停止注入进程，模式切回integrated；实体开关选择，IR POWER或呈现红2启动。覆盖真实搜索→发现→驻留确认→对准→接近→停靠，六车位、丢失、障碍、无回波和急停分别记录。可断开电脑，正常任务不依赖主机续租。同场景下SW8正常/旁路各三次，记录真实任务时间、停车误差和画面变化到UART响应延迟。

目前速度下从1 m到350 mm仅理想行驶就约15秒，扫描和确认会增加时间。最终指标以本次实测冻结，不沿用旧proposal的12/18秒目标。

## 构建与验证

本次E12成功构建位于`build/member_b/20261104T192605_706632Z_build/`，原始SOF为该目录`source/quartus/output_files/PartBDebug.sof`，**6706156字节**，已实际下载并核对E7070012。当前发布副本为`firmware/E7070012/PartBDebug.sof`，与本次成功原产物逐字节一致；仅保留这一份最新release副本，旧E11产物仍可从原build与Git历史追溯。

E6首次Full Compilation目录`build/member_b/20261104T144730_277631Z_build/`的最终`result.json`为 **FAIL**。Quartus编译工具退出0、耗时1183.703秒且fit成功，但两条critical timing warnings在构建警告检查时导致拒收，**未执行独立`timing_gate`步骤，也未生成`timing.json`**；工具退出0不等于本工程时序验收通过。实际STA路径随后定位并用于E7修正，E7独立构建现已通过。E6失败仍保留，E6从未下载，不把新结果回写成旧版通过。

本次发布buildId为 **E7070012**，BCTL/CCTL均由生产顶层传入实际设计ID，须使用配套新版主机/Tcl。控制、R6、完整构建/post-fit、下载与停车pulse均有本版独立证据；原始SOF为`build/member_b/20261104T192605_706632Z_build/source/quartus/output_files/PartBDebug.sof`、6706156字节。`echo7.py program`核对源码和本机成功构建记录；地面五轮仍未证明主线搜索停靠完成。

先确认Python路径与Quartus工具可用；如尚未安装工程Python依赖，可执行`& $pythonExe -m pip install -r requirements.txt`。依赖安装不属于R6计时。

```powershell
& $pythonExe tools/echo7.py build
& $pythonExe tools/echo7.py program
& $pythonExe tools/echo7.py test --rtl --only tb_control_repair tb_chassis_debug tb_pixel_uart_repair
```

也可在Quartus打开QPF执行Full Compilation；`quartus/output_files/PartBDebug.sof`是直接工程编译的默认位置。`echo7.py build`使用独立本次构建目录，实际SOF路径以成功记录为准。上面的`program`自动使用本机最近一次成功构建记录的SOF，也可用`--sof`显式提供该记录对应的绝对路径；它核对本次构建来源和产物，不能用旧SOF代表新功能。

发布文件使用固定路径：[E7070012 FPGA程序](firmware/E7070012/PartBDebug.sof)、[集成版数据表PDF](docs/ECHO7_Integrated_Datasheet.pdf)。E12 SOF为**6706156字节**，复制自成功构建且已实际下载的E12产物。直接使用发布SOF时，在Quartus Programmer选择实际USB-Blaster和FPGA链位置2，添加该SOF并执行Program/Configure；本板下载后应由BCTL读回`buildId=0xE7070012`。链位置2是这块实际DE1-SoC的枚举结果，换板时先确认设备链。

预编译SOF不包含本机`echo7.py`成功构建记录，因此直接下载采用Quartus Programmer；`echo7.py program`仍只接受与本机成功构建记录相符的指定产物，不放松其来源保护。SOF配置是易失的；掉电后需重新配置，本文没有声称完成永久启动镜像部署。

掉电后先重新下载并核对所用固件的BCTL版本，再用`mode vision`保持零速，读取当前配置、阈值和标定状态；不要沿用上次会话的cfg/tag或已校色结论。已实际完成的E7070004重下记录中，摆位检查的6对读数均恢复蓝1健康/锁定，使用新上电默认红48/蓝20、配置0，尚未校色或扫描标定。扫描标定也会随KEY0/重新配置失效；只有已有适用的三次地面实测记录，才能重新设置实测秒数和`--calibrated`。重下及恢复证据见[修复记录](docs/REPAIR_RESULT.md)，该历史复验没有重跑或替换既有R6、Full Compilation结果，E5下载另有本版记录。

一页产品数据表由`tools/render_integrated_datasheet.py`生成，讲述功能、组件、模式、红蓝牌、拨码/按键、VGA与数码管用法；设计版本从RTL header读取。编译及实机指标保留在`docs/integrated_datasheet_metrics.json`与修复记录中，不再堆入产品页。生成依赖属于独立文档工具，不需要改动主视觉环境的`requirements.txt`：

```powershell
& $pythonExe -m pip install reportlab pypdf
& $pythonExe tools/render_integrated_datasheet.py
```

本机已有当前成功构建记录时，可导出整项目交接ZIP：

```powershell
& $pythonExe tools/export_submission.py --out build/echo7_submission.zip --datasheet docs/ECHO7_Integrated_Datasheet.pdf
```

导出核对当前源与成功构建，拒绝旧SOF或覆盖已有ZIP。包中仅有一份SOF，使用对应成功构建的`firmware/<BUILD_ID>/PartBDebug.sof`；本次发布文件为`firmware/E7070012/PartBDebug.sof`，以E12自己的成功构建记录和原始SOF导出，不使用E11产物。不再另放`verified/PartBDebug.sof`副本。保留中英文README、工程/RTL/TB/工具、真实回放输入和文档；排除编译数据库、私有工具链与无关运行缓存。一页PDF不要求SHA sidecar，压缩包做CRC检查；对话记录只有显式指定已检查的导出manifest才会加入。新的克隆没有本机成功构建记录时，应先自行构建再运行导出器。ZIP完整性通过不增加任何实机验收结论，也不执行Git提交或上传。

| 已实际生成的版本 | 本次独立构建产物路径 | 构建状态 |
|---|---|---|
| E7070002 | `build/member_b/20261104T100141_653795Z_build/source/quartus/output_files/PartBDebug.sof` | PASS，已下载并记录该版硬件结果；历史产物不作为本次发布文件 |
| E7070003 | `build/member_b/20261104T104155_505074Z_build/source/quartus/output_files/PartBDebug.sof` | PASS，已下载；现场坏帧恢复已验证；历史产物 |
| E7070004 | `build/member_b/20261104T111202_124373Z_build/source/quartus/output_files/PartBDebug.sof`；历史产物 | Full Compilation **PASS**；2026-11-04 22:31:50 AEDT实际下载且BCTL版本核对 **PASS**；红2重新选择/新锁/启动已观察，用户确认蓝1离开后实物停车 |
| E7070005 | `build/member_b/20261104T134331_185490Z_build/source/quartus/output_files/PartBDebug.sof`，6706157字节；历史产物 | Full Compilation、门检、实际下载及BCTL E7070005读回 **PASS**；真实蓝1地面任务最终NOT_FOUND，未停靠 |
| E7070007 | `build/member_b/20261104T151422_461823Z_build/source/quartus/output_files/PartBDebug.sof`，6706155字节；历史原始产物保留，旧发布副本已替换 | Full Compilation/post-fit、实际下载及BCTL E7070007读回 **PASS**；随后真实任务未完成停靠，详见第01–05轮记录 |
| E7070008 | `build/member_b/20261104T160829_127927Z_build/source/quartus/output_files/PartBDebug.sof`；6706156字节，历史原产物保留，旧发布副本由E9替换 | Full Compilation/post-fit、实际下载及BCTL E7070008读回 **PASS**；真实蓝1任务板上DOCKED及零速驻留已记录，用户确认持续前进、无明显偏转，探头前端终距约335 mm |
| E7070009 | `build/member_b/20261104T171519_480274Z_build/source/quartus/output_files/PartBDebug.sof`；6706161字节，历史原产物保留，旧发布副本由E10替换 | Full Compilation/post-fit、实际下载及BCTL E7070009读回 **PASS**；画外蓝4实机 **INCOMPLETE**，曾发现/锁定但60秒观察窗内未DOCK；反向SEARCH未触发，主机STOP零速收尾 |
| E7070010 | `build/member_b/20261104T175030_045504Z_build/source/quartus/output_files/PartBDebug.sof`；6706157字节，历史原产物保留，旧发布副本由E11替换 | Full Compilation/post-fit、下载及版本核对PASS；画外蓝4实机NOT_FOUND/SCAN_BUDGET、未DOCK，无反向SEARCH；V1未ARM零速收尾 |
| E7070011 | `build/member_b/20261104T182211_444905Z_build/source/quartus/output_files/PartBDebug.sof`；6706153字节，历史原构建保留；旧release副本由E12替换 | Full Compilation/post-fit、实际下载/身份、停车调参PASS；真实搜索两轮NOT_FOUND、短时对照三轮INCOMPLETE。实验参数未固化进SOF，默认4/4/5/3/30不变 |
| E7070012 | `build/member_b/20261104T192605_706632Z_build/source/quartus/output_files/PartBDebug.sof`；当前发布`firmware/E7070012/PartBDebug.sof`，6706156字节 | Full Compilation/post-fit/实际下载及静止pulse PASS；五轮实物结果保留，未DOCK，volatile实验设置不固化进默认SOF |

课程R6正式入口仍为 `./run_all_tests.sh`，要求clean copy、Verilator **5.050**、模块与系统自检、故意坏模块输出CAUGHT；本次用户目标为≤285秒（课程门槛300秒）。本机可用下列包装命令调用同一Bash入口，默认4任务编译；本轮完全相同的编译输入通过内部哈希缓存共享一次新编译，所有场景仍独立运行断言，不读取往轮二进制：

```powershell
& $pythonExe tools/run_r6_windows.py --compiler-bin 'C:\msys64\mingw64\bin' --bash 'C:\Program Files\Git\bin\bash.exe' --jobs 4
```

ModelSim通过不等于R6通过；各版规定环境内真实执行结果见验收记录。较完整历史视觉/Python回归按变更需要另跑，不用重复运行所有历史测试堆数量。

E7070004正式R6已在干净副本用Verilator5.050实际完成：**219.556074秒、退出0、12项及CAUGHT全部PASS、targetMet=true**，记录为`build/member_b/20261104T110801_416299Z_verilator_course/result.json`。此前E7070002为245.451876秒，E7070003为221.258456秒。加速来自同一次调用内按完全一致输入哈希共享新编译、独立continuous/overload场景并行及4任务编译；没有降低25fps输入速率、删除断言、force观察结果或复用上一轮二进制。故意坏模块仍必须由真实断言捕获。

E5首轮正式R6保留为 **FAIL，303.500928秒，退出1，targetMet=false**：包含新超声代表项的前12项已PASS，但`mainColourSupportReader_tb`编译触及300秒完整套件截止，最后一项及故意坏模块CAUGHT未完成。记录为`build/member_b/20261104T133634_057221Z_verilator_course/result.json`。

随后E5最终正式R6以61个源文件的本轮新编译完成：**239.403059秒、退出0、13项PASS＋1项CAUGHT、targetMet=true**，满足≤285秒目标。记录为`build/member_b/20261104T140614_115616Z_verilator_course/result.json`。这是单独完整执行的结果，不是沿用E4用时或把前轮子项拼成通过；首轮失败记录不覆盖。

`tb_control_repair`验证one-hot/模式/搜索/驻留/安全/负例及实际UART JSON；`tb_board_repair_pins`使用真实NEC脉冲、J3 TRIG/ECHO模型与115200 UART，无force控制器输入；像素系统链使用真实perceptionCore输入，合成视觉调试与真实相机回放各自明确标注。旧集成bench曾使用三位编码和锁死超声等旧语义，历史PASS不能沿用当前版本。

E5定向证据单独记录：`turn_e5/control_negative.log`为生产TURN_SIGN=−1下269检查PASS；同bench正号泛型对照也通过，不累加成538个独立需求。两次ModelSim含编译共3.367385秒。`turn_e5/pixel/`为显式负号、原12帧25fps真实perceptionCore像素→C→实际UART管线，12报告PASS，总84.364643秒（编译12.529247、仿真71.835396）。`sonar_guard_verilator_20261104T133057_380747Z/`为完整真实时钟TRIG/ECHO专项46检查、12采样、11触发PASS，总89.573秒（编译5.821、仿真83.749）；以上路径均位于`build/remaining_20261104/`。旧ModelSim超声运行因耗时及源边界复核中断，日志保留为INTERRUPTED，不当通过。随后同一sonar TB新增显式`+R6_REPRESENTATIVE`六事务入口，覆盖正常、近距、FAR、无上升、卡高/迟落和恢复，完整默认边界路径保留；正式R6已加入该代表项，并保留原12项与CAUGHT。**这些定向结果不替代E5完整R6或实机验收；时序通过来自独立Full Compilation结果。**

超声代表入口已另行通过25检查、6采样、6触发，保持实际时钟、模拟602 ms；编译5.834637秒、仿真38.076932秒、总43.912875秒，证据为`sonar_guard_representative_20261104T133440_446720Z/validated_result.json`。一次性启动器曾因PASS行新增scope字段而误判，原包装器FAIL单独保留；正式R6通过判定器核验实际exit0及`PASS ... scope=R6_REPRESENTATIVE`日志，未重跑或改写仿真。该代表路径也包含在上述E5最终完整R6中。

E6正式R6单次完整运行 **PASS，266.840318秒，退出0，13项PASS＋1项CAUGHT，targetMet=true**；Verilator5.050、4任务编译、61个源文件均为本轮新编译。结果为`build/member_b/20261104T144856_668139Z_verilator_course/result.json`。这对应首次因时序critical warnings被拒收的同次源码，证明该次功能仿真达到≤285秒目标，不证明时序或硬件通过；后续实际路径修正不能自动继承此源码的结果。

E6聚焦控制回归已通过：生产`TURN_SIGN=-1`及泛型`+1`对照分别为 **338检查、53条完整UART**，编译加两次ModelSim共 **5.2128905秒**，记录`build/remaining_20261104/control_e6_20261104T144617Z/result.json`。这是同一需求集的两种方向参数验证，不累加为676个独立需求。

E6真实像素→perceptionCore→C→实际UART独立运行一次 **PASS**，记录`build/remaining_20261104/pixel_uart_e6_20261104T144702_631205Z/result.json`：编译 **9.217031秒**、仿真 **69.766992秒**、总 **78.991060秒**。固定25fps的 **14帧/14报告**，仅将原居中段从2帧增加至4帧以满足新停车边界后的三帧确认，保留旧帧与断言；UART计数search41、left18、forward19、right34、zero178。bench将驻留缩短为1 ms，不等于实测或完整模拟板级1.5秒机械停稳；未force内部观察。完整R6结果另列于上文，聚焦仿真仍不替代Full Compilation或实机验收。

E7正式R6单次完整执行 **PASS，265.276162秒、退出0、13项PASS＋1项CAUGHT、targetMet=true**，Verilator5.050、4任务编译、61个源文件本轮新编译，满足≤285秒目标。证据为`build/member_b/20261104T151442_166532Z_verilator_course/result.json`；这是E7自己的完整结果，不继承E6的266.840318秒。E7完整构建及实际下载随后通过，真实任务结果另外列出，不能由仿真通过替代。

E7聚焦结果为`build/remaining_20261104/control_e7_20261104T151338Z/result.json`：默认256种U输入算术等价，生产负号/泛型正号两种TURN_SIGN各 **338检查、53完整UART PASS**，编译及两次仿真共 **5.113292秒**，不重复计为676个独立需求。首次`control_e7_20261104T151306Z/`发生词法编译失败，补空格后纠正；原失败记录保留。聚焦检查不替代独立完整R6、构建或实机结果。

E8聚焦控制结果为`build/remaining_20261104/control_e8_20261104T160731Z/result.json`：生产`TURN_SIGN=-1`与泛型`+1`各 **433项检查、88条完整UART PASS**，编译0错误/0警告，编译加两次仿真共 **6.7496263秒**。覆盖新增远/近、左右差速以及原有ALIGN、边界重确认、控制与安全要求；两种参数配置不累加为866个独立需求。

E8正式R6单次完整运行 **PASS，270.641086秒、13项PASS＋1项CAUGHT、targetMet=true**。Verilator5.050使用4个编译任务、2个仿真并发，在干净副本内对61个源文件重新编译；证据为`build/member_b/20261104T160829_370108Z_verilator_course/result.json`。这是E8自己的功能验证，符合≤285秒目标，不继承E7结果，也不代替另列的Full Compilation或E8实机验收。

其中像素→真实perceptionCore→C→序列化UART保留原 **14帧/14报告、固定25fps**和原目标编号/位置顺序，无内部观测force。PASS计数为search41、left18、forward19、rightCorrection34、zero177、coarseRight34、rightSpin0；coarseLeft/fineLeft/fineRight均为0。实际U160且已处于APPROACH时，完整UART精确对应逻辑3/5前进右纠偏，不能用原地右转充数；左差速与近距4/3组合由控制专项覆盖，不声称本像素场景也触发了它们。停车、新采集边界后三个独立帧及最终STOP断言保留，bench的1 ms驻留仍不等同板级1.5秒实物停稳。

E9定向控制回归为 **PASS**：ModelSim生产`TURN_SIGN=-1`与泛型`+1`各 **696项检查、245条完整UART**，编译0错误/0警告，编译加负/正两次实际仿真共 **20.8500433秒**。证据为`build/remaining_20261104/control_e9_20261104T171519Z/result.json`，覆盖有限回扫、同一预算/任务时间、停车重确认、原有控制/安全及完整UART；两个参数配置不重复累加为1392项独立需求。首次主机PASS匹配器漏写冒号，误报FAIL，保留在同目录`wrapper_result_initial.json`；负号仿真本身第一次已PASS，没有重跑，只用同一已编译库补跑此前未运行的正号配置，不能将包装器误报说成RTL失败。E9保留原14帧固定25fps像素输入、顺序与断言；正式R6随后独立通过，详见下文；Full Compilation/post-fit及下载身份读回随后也已通过，实机回扫结论另列。

上述20.8500433秒是编译及两次仿真调用的累计执行耗时，不包含修正宿主匹配器期间的等待。回扫检查保留150000逻辑微秒的门限，但TB的共享时基每20 ns时钟增加1、UART为加速模型，驻留也缩短；因此它验证逻辑边界和完整报文，不代表已在真实管脚上测得150 ms脉宽或车体停稳。

E9正式R6单次完整运行 **PASS，274.530007秒、退出0、13项PASS＋1项CAUGHT、targetMet=true、cleanBuild=true**，满足≤285秒目标。证据为`build/member_b/20261104T171630_007376Z_verilator_course/result.json`。原14帧固定25fps像素测试未改并通过，控制专项在Verilator中也完成696检查/245条完整UART。该结果属于E9自身，不继承E8的270.641086秒；Full Compilation/post-fit与下载随后独立通过；R6本身不替代时序或实物回扫验收。

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
| E7070004，SW6/7实物显示 | 用户确认SW6颜色信息及两页自动交替；当时6个候选，第二页为空符合槽位分配。SW7白色空隙显示颜色/“无标牌”；移动纸张使完整蓝1框覆盖中心后，用户确认`ID:B1` | 见[修复记录](docs/REPAIR_RESULT.md)；已恢复SW0单独选择。UNKNOWN/拒识原因的实际显示、16槽同时占满及中心歧义场景仍未确认 |
| E7070004，合成视觉＋真实J3停靠 | 434个状态快照、78.931565秒；实际517mm时逻辑+5/+5，446mm时+3/+3，347mm首次DOCKED并撤权/零速；退远至534–615mm，2.194秒内12个快照仍DOCKED/零速 | `build/continuation_20261104/dock_hardware_01.jsonl`及`dock_analysis.json`；用户确认运动→减速→停止→退远不重启；底盘架空，不代表地面停靠误差 |
| E7070004，真实J3近停/滞回/恢复及独立STOP | HOLD03共469个状态快照、86.677721秒，6项条件PASS、该脚本无未验证项；近停、滞回仍停、退远恢复及随后STOP均获用户确认 | `build/continuation_20261104/hold_hardware_03.jsonl`及`hold_analysis_03.json`；合成视觉、真实IR/J3/UART、架空；本轮未观察轮向，未测机械停车延迟 |
| E7070004重下后，42cm静态SW8三对 | 正常/旁路各36对，共72对，C/B各72个不同帧；所选蓝1全部健康/锁定、未ARM且零速。正常六蓝牌各36/36接受；旁路蓝2为35/36，其余各36/36 | `build/remaining_20261104/sw8_comparison_confirmed.json`及`sw8_analysis.json`；同场景条件获用户确认，保留一次读取不确定（reason3）；VISION_ONLY静态结果，不代表地面旁路闭环或图像到UART延迟 |

E4触发后的约2秒继续读取状态而不发送心跳：13个采样均保持ARM且`leaseValid=0`，其中7个ALIGN、4个LOST、2个ACQUIRE。含触发采样共8个运动命令采样，**不能写成连续稳定转动2秒**；短暂视觉丢失时FPGA进入零速重确认。该次结束BCTL为frame2959、E7070004、好帧、蓝1质量255、U182/V130、101×117框、处理47.652ms，红2事件7/id2。此记录证明红2→新请求锁定→启动及INTEGRATED无需心跳；用户实物确认启动，并澄清“蓝一脱离后就停车了”。主机2秒STOP只独立确认板上撤销/zeroSent，其物理停车时刻未单独测量；不能把用户观察的停车归因于主机STOP或后续mode1切换。最终VISION_ONLY读回未ARM、逻辑零速，用户确认已停止。本轮不据此宣称六车位落地停靠或机械停车延迟已验收。

后续六档观察保留441个不同B帧和405个不同C缓存帧；C/B分别冻结，不要求每对同帧。主要蓝1–6区间的C锁定次数分别为197/200、22/23、24/28、16/22、23/29、26/30；另有一次未锁定的蓝2短过渡，冲突后返回蓝1为62/64。27次冲突中26次是持续稳定的mask3，另一次为mask6过渡；所有无选择/冲突样本均无C健康/锁定且B未选择目标。返回蓝1的首个样本保留旧CLEAR报告，C没有把它当作新锁。7个坏B帧均为candidateOverflow，之后均观察到好B帧；并非每个坏帧都在同一选择结束前观察到重新锁定。六档覆盖由此成立，但不是441次全时锁定或六车位落地通过。完整区间表和坏帧索引见[修复记录](docs/REPAIR_RESULT.md)。SW6/7目前只获得上表所列部分显示确认；后续SW8静态对照另行记录，不能混作这次六档结果。

重下后的SW8三对使用用户确认的相机至标牌42cm、同一摆位/光照及红48/蓝20。首会话完成第一对后等待拨码超时，原结果仍为PARTIAL；剩余四段在新会话续采，没有重采或覆盖第一对。操作者确认跨会话条件未变后，比较器给出COMPARISON_VALID；72对是各端分别冻结的采样，不是相机全部原生帧或C/B同帧。一帧旁路蓝2读取不确定被如实保留。详细逐段统计与采集至处理完成时间见[修复记录](docs/REPAIR_RESULT.md)；该时间不是图像变化到UART响应时间，底盘落地但全程零速也不构成地面闭环试验。

后续显示检查及摆位后的地面预检读到cfg7、已校色、J3=386mm且有效，蓝1健康/锁定；VISION_ONLY、未ARM、零速、IR未急停，扫描仍为10秒/未标定。该快照只读CCTL，未读取新B颜色配置，因此不推测当前阈值；前述红48/蓝20、未校色仅属于SW8采样窗口。此预检尚未启动地面第一圈，后续运动结果独立记录，见`build/remaining_20261104/ground_preflight_status_01.json`及[修复记录](docs/REPAIR_RESULT.md)。

J3续测使用合成视觉、真实测距/IR/UART和架空底盘。停靠记录中的517→446→347mm是首次状态变化的实测读数，不是尺子标定后的精确边界；条件确认点521/454/321mm是随后不同快照。首次DOCKED后83个快照、14.853秒内保持撤权/零速，包含反射板退远后2.194秒的确认窗口。用户确认这一实物过程；最终回到VISION_ONLY、IDLE、未ARM、零速。没有据此测得落地停车距离误差。

HOLD03的危险距离确认窗口为231–242mm、5个快照/0.647892秒；滞回窗口254–292mm、7个快照/1.163541秒均保持HOLD/零速。退远至367–407mm后，19个快照/3.119478秒观察到ALIGN及逻辑−4/+4。80.491761秒显式发送TX4 STOP，继续同一模板和心跳；STOP ACK至末样本6.093588秒内，34个不同帧的状态快照均未ARM、零速且zeroSent=true。其首末快照跨度为5.919557秒，原生frameId推进147；实际J3为367–376mm，租约、来源和目标锁定有效，无sonarHold/IR/fatal，模式、选择、tag和配置不变，之后才切到VISION_ONLY。用户确认“近停、滞回仍停、退远恢复、随后自动停”，未观察轮向。这里34次是状态轮询，不是34次独立测距；持续状态指全部记录样本，不测机械停车延迟，也不补证此前红2那次未隔离的STOP时刻。

前两次HOLD记录保留：HOLD01有362个快照/66.181秒，板上检查PASS，但用户未确认实物全过程并要求重做。HOLD02有434个快照/79.899秒，保留原FAIL；实测距离在滞回区间未连续保持主机要求的1秒便进入恢复范围，末状态已到313mm、ACQUIRE、仍ARM，主机却把阶段未完成当作失败立即STOP，截断恢复观察，用户因此未看到恢复。这不证明生产RTL恢复缺陷。一次性验收脚本已改为提前安全恢复时记录NOT_VERIFIED并继续、最终给PARTIAL；HOLD03完整满足各阶段，无跳过。生产恢复条件始终是连续三个新的有效测距≥300mm，1秒仅为本次滞回观测要求。脚本修复没有更改RTL/SOF；HOLD03清理正常。

构建资源/时序也按版本保留：E2为29417/32070 ALM，最差setup1.164ns、hold0.078ns；E3为29373/32070 ALM，最差setup0.967ns、hold0.117ns。两版M10K357/397、DSP51/87，未约束项0、四角及CDC检查通过。

**E4完整编译PASS**：1121.141秒，post-fit门检25.868秒，0 error、92 warnings；29576/32070 ALM（92%）、41000寄存器、M10K357/397、DSP51/87、2802640 memory bits、2个PLL。四角最差setup **+1.633ns**、hold **+0.118ns**，未约束项0；88项检查及每角63条同步链覆盖PASS，MTBF为NOT_ASSESSED。下载记录为`build/repair/program_e7070004_console.log`，板上BCTL已核对E7070004；硬件红2测试另行记录，编译/下载通过不替代运动验收。

**E5 Full Compilation PASS：**编译1173.143秒、post-fit门检25.799秒，0错误、92警告；ALM **29507/32070**、寄存器40957、M10K357/397、DSP51/87、PLL2。最差四角setup **+2.089 ns**、hold **+0.116 ns**；88项检查、所有未约束项为0、每角63/63同步链覆盖均PASS，MTBF仍为NOT_ASSESSED。完成时刻为2026-11-05 **01:03:31 AEDT**，这是构建完成时刻，非下载时间。对应`build/member_b/20261104T134331_185490Z_build/result.json`及`timing.json`。随后原始SOF成功下载并读回E7070005，记录`build/remaining_20261104/program_e5_console.log`，UTC时间2026-11-04T14:11:16.707754（AEDT次日01:11:16.707754），并已复制到发布路径；不能把下载成功当作地面任务通过。

**E6首次Full Compilation验收FAIL：**fit已成功，ALM **29462/32070（92%）**、寄存器41136、M10K357/397、DSP53/87、PLL2。CLOCK_50在Slow85角setup为 **−0.265 ns**、TNS **−1.786 ns**，Slow0角setup **−0.203 ns**；最差hold **+0.120 ns**。Quartus编译工具1183.703秒、退出0，仍因两条critical timing warnings被构建警告检查拒收，最终结果退出1；证据`build/member_b/20261104T144730_277631Z_build/result.json`及该目录原始STA报告。功能R6通过不能覆盖负setup；详细路径诊断随后用于E7并取得本版独立构建通过，E6失败与从未下载的历史不变。

实际STA定位记录`build/remaining_20261104/e6_sta_diagnosis_20261104T150928_837210Z/`耗时 **13.098885秒**，指出路径为`mode → adapter fence → 32位abs → 两个DSP → clamp → alignPulseUs`，据此实施E7默认算术窄位路径。该耗时是诊断报告生成时间，**不是时序通过结果**；E6负setup和未下载状态保留，E7通过来自其独立post-fit结果。

**E7 Full Compilation及post-fit PASS：**编译 **1147.755秒**、门检 **26.087秒**，0错误、92警告；ALM **29320/32070（91%）**、寄存器41015、M10K357/397、DSP51/87、PLL2。最差四角setup **+0.864 ns**、hold **+0.117 ns**，88项检查、未约束项0、每角63/63同步链覆盖PASS，MTBF未评估。证据为`build/member_b/20261104T151422_461823Z_build/result.json`与`timing.json`，原始SOF6706155字节。随后实际下载并读回E7070007，日志`build/remaining_20261104/program_e7_console.log`，UTC **2026-11-04 15:34:42.428181**（AEDT次日 **02:34:42.428181**）。

**E8 Full Compilation和post-fit PASS：** 构建目录为`build/member_b/20261104T160829_127927Z_build/`，编译 **1159.722秒**、独立门检 **25.963秒**，0错误、92警告、无critical warning；**29281/32070 ALM（91%）**、41081寄存器、357/397 M10K、51/87 DSP、2 PLL。最差setup **+1.021 ns**、hold **+0.121 ns**，88项时序检查全部通过、所有unconstrained为0，四角均完成63/63同步链覆盖；MTBF未评估。证据为该目录`result.json`与`timing.json`，原始SOF **6706156字节**，位于`source/quartus/output_files/PartBDebug.sof`。

E8原始成功产物已实际下载，BCTL读回E7070008；`build/remaining_20261104/program_e8_console.log`记录UTC **2026-11-04 16:28:58.446132**（次日 **03:28:58.446132 AEDT**）。在同一塑胶地面与适用条件确认后，`e8_scan_calibrated_13600ms.json`读回13.6秒扫描标定；VISION_ONLY、未ARM、零速。`e8_blue1_centre_preflight.json`的4对样本均锁定真实蓝1、U123，实际J3 687–690 mm。它们证明下载、预算恢复及零速预检；随后真实蓝1任务的板上DOCKED与实物确认范围另行记录，不能从预检本身推定停靠。

E7下载后，在同一塑胶地面、供电及SEARCH 4 cm/s未变的适用条件确认下恢复13.6秒，`build/remaining_20261104/e7_scan_calibrated_13600ms.json`读回`scanBudgetUs=13600000`、`scanCalibrated=true`、`scanBasis=CALIBRATED_TIME`；VISION_ONLY、未ARM、L0/R0、zeroSent=true、IR=false，J3=694 mm且有效，真实来源健康但目标NOT_FOUND。这是下载后的零速及预算恢复快照；后续KEY0重置和第01–05轮真实任务另列如下，该快照本身不证明对准或停靠通过。

E5下载后的零速实机记录均为VISION_ONLY：`build/remaining_20261104/e5_zero_scene_01.json`保留8对完整C/B读数、各8个不同帧，蓝1健康且锁定8/8、全部零速，颜色配置1且已校色，红24/蓝16。随后`e5_far_01.json`保留真实空旷6对读数，全部`distanceMm=4000`、`distanceValid=true`、`distanceKind=FAR`、`sonarHold=false`、`zeroSent=true`；用户明确看到d页` FAr`。FAR轮的源健康但目标锁定0/6，未把空旷记录写成蓝1锁定。两轮分别冻结C/B，不声称同一原生帧；FAR是远距哨兵而非实测4米。这确认新固件的空旷读数与显示，后续三次地面整圈见下文，六车位运动闭环尚未完成。

E4地面首轮`ground_scan_01.jsonl`为TRIAL_INVALID：78快照、21.518290秒，12个SEARCH运动快照为逻辑−4/+4；累计SEARCH命令2.899142秒后，真实`4000,false`使HOLD/零速/zeroSent先于主机清理STOP出现，清理无错误。用户观察约75°后自停，并确认俯视顺时针。当前地面已更正为**塑胶地板**；日志早先“epoxy”口述保留但不能算环氧树脂数据。该次没有完整一圈、未写入扫描标定，也不按75°比例推算整圈时间。实测车体左右与U方向的对应随后促成E5转向修正；新的FAR语义来自用户后续需求，不回改旧E4的失效记录。

E5已取得 **3/3次完整圈实物观察**，均在当前塑胶地面、逻辑+4/−4旋转，未出现HOLD。记录为`build/remaining_20261104/ground_e5_01.jsonl`、`ground_e5_02.jsonl`、`ground_e5_03.jsonl`；下表时间为累计SEARCH命令时间，FAR列为运动状态快照数，不能当作独立超声采样数。

| 次数 | SEARCH时间 | 运动快照 / 其中FAR | 用户实物观察 |
|---|---:|---:|---|
| 1 | 13.561176秒 | 80 / 10 | 逆时针完整一圈、约超转10°、前移3.5 cm；起步出现单侧前冲 |
| 2 | 11.075500秒 | 66 / 13 | 完整一圈、约超转5°、前移2 cm；起步出现单侧前冲 |
| 3 | 11.436358秒 | 70 / 15 | 完整一圈，用户说明按A晚了、约超转45°；未见单侧前冲，未提供位移 |

三次时间极差 **2.485676秒**。这些停止时刻包含用户按A的反应及超转，不能视为精确360°计时，也未验证固定13.6秒自动停止的角误差。首圈197个快照/34.960365秒，运动窗口源、租约、有效J3健康，70个实测距离快照377–3120 mm；最长连续FAR观察首末相隔1.072009秒。IR A先于主机STOP撤销ARM并归零，清理回VISION_ONLY、IR锁存、零速。实际逆时针已证实方向纠正，但前两圈单侧前冲和位移保留为机械/驱动表现，根因未定位；相同的轮速命令不证明两轮同步起步。

本次取最大实测命令时间向上舍入至 **13.6秒**并实际写入，`e5_scan_calibrated_13600ms.json`读回`scanBudgetUs=13600000`、`scanBasis=CALIBRATED_TIME`、`scanCalibrated=true`，VISION_ONLY、未ARM、IR锁存、L0/R0、`zeroSent=true`。该标定仅支持当前地面的有界近似扫描，不能保证未来每次恰好360°；换到实验室环氧树脂地面尚需实测。后续下载会清掉本会话设置；在同一场地、底盘和轮速条件已确认仍适用时，可恢复13.6秒，无须把重复三圈当作新增进度。真实蓝1任务的后续失败如下，六车位闭环未完成。

E5真实相机蓝1落地任务`build/remaining_20261104/integrated_blue1_01.jsonl`保留656个状态快照，任务观察约36.330秒。启动后约1.2秒首次进入ACQUIRE，但未完成驻留后的目标确认；继续搜索，到累计SEARCH约11.2秒时第二次ACQUIRE才接ALIGN。随后有9段ALIGN和8段LOST，仅5个APPROACH快照，实测距离613–663 mm。累计SEARCH到13.6秒后，控制器自动进入`NOT_FOUND/SCAN_BUDGET`、撤销ARM并归零，**不是DOCKED**。用户观察为首次扫过未留住、第二次跟踪靠近后左右摆动并转远。这次记录是CCTL状态，缺少连续BCTL U轨迹，不能把所有失锁都归因于坐标符号。

随后的`real_turn_probe_e5_01.jsonl`为 **INCOMPLETE**：要求的3个停车后锁定帧只取得2个，不能改记通过。固定蓝1的转前U为57、57、57；真实逻辑+4/−4从启动到主机STOP请求约0.340987秒，记录7个正确ALIGN快照，清理无错误；该间隔不是实测轮子运动时长。最早VISION_ONLY且zeroSent的FPGA时刻为1542683620 µs；以此为基准，后续实际captureStart在+245.133 ms为U96/锁定、+525.021 ms为U142/未锁定、+884.877 ms为U169/锁定；到+90.489–92.608秒的另6帧才记录静止U173。用户确认纸张固定且最终车轮已停，未确认尾转持续时间。因此，方向使U先朝中心变化，但随后明显越过中心；200 ms之后图像仍移动，不能从稀疏快照推导精确机械停车时间，更不能把候选1.5秒当成已测停稳。

E7实机已使用`--with-vision`同时保留CCTL和BCTL，原始记录与用户反馈汇总在`build/remaining_20261104/e7_operator_notes.json`。本地`integrated_task_observer_e7.py`核对E7版本，默认不发START、心跳或合成观察；第01–03轮记录实体POWER，第04–05轮另外明确使用一次HOST START、真实相机，不能混称遥控启动验证。完整BCTL按约0.2秒读取间隔目标额外采样，实际耗时随JTAG读取而变；每次记录起止时间，C/B分别冻结，不声称同帧，稀疏轮询也可能漏过短状态。各轮均保留自身截止原因和STOP→VISION_ONLY清理结果。

| E7实际窗口/试验 | 真实记录与结果 | 实物反馈和解释范围 |
|---|---|---|
| 第01轮，POWER | `integrated_blue1_e7_01.jsonl`：147个C快照均IDLE/零速，启动窗口到期，INCOMPLETE | 用户随后说“按了power，没反应”，又说“按了好多次，没反应，然后重启后动了一下又不动了。再次重启后又动了一下。”，确认复位方式KEY0。缺同步IR/运动轨迹，不能判定短动原因或精确按键时序 |
| KEY0后检查 | `e7_after_key0_pairs.json`：6对中C健康5/6，一帧候选溢出后恢复；J3从92 mm/HOLD到792 mm/HOLD，再到788 mm解除 | KEY0恢复INTEGRATED/未ARM及默认10秒未标定。核对E7后置VISION_ONLY零速，清场，再由`e7_scan_restored_after_key0.json`读回恢复13.6秒 |
| 第02轮，POWER | `integrated_blue1_e7_02.jsonl`：首见ARM在主机20.038747秒，261个C/258个B，任务观察60.015279秒；SEARCH→ACQUIRE→SEARCH→215 mm HOLD→319 mm SEARCH→33 mm HOLD，随后约251 mm保持；累计SEARCH4.512126秒，截止后INCOMPLETE | 用户：“扫过了蓝1，继续转的时候，遇到了线缆缠绕，然后超声波判定到距离过近中止”。B采样全好帧/NOT_FOUND，无溢出；未采到ALIGN、APPROACH、DOCKED或蓝1锁定。证明本轮实际启动和近距阻挡，不能记为停靠 |
| 第03轮，POWER | `integrated_blue1_e7_03.jsonl`：140个C/138个B，45秒启动窗口在B读取期间到期；无ARM，INCOMPLETE | 用户：“按了很多次power，都没反应”。没有精确IR接收/按键时间，不推断硬件IR损坏或按键与窗口的先后 |
| 第04轮，一次HOST START | `integrated_blue1_e7_04.jsonl`：预检4/4不同帧锁定蓝1、U112、J3 698–699 mm；206个C/201个B，60.1635664秒任务观察；先APPROACH +5/+5，再反复短ALIGN/ACQUIRE，末J3 684 mm；无DOCKED、INCOMPLETE | 用户：“车刚刚在向前蠕动，有点像往前走，但是右轮蠕动幅度明显更大”；“左轮基本没动，就只动了一点点，大概1cm，右轮动了3.5cm”。这是含初始直行的整轮净轮程口述，不是单个脉冲位移 |
| 第05轮，一次HOST START | `integrated_blue1_e7_05.jsonl`：预检3/3不同帧锁定、U197、J3 669 mm；56个C/51个B，15.048011秒；U197→193→186→132→123，进入APPROACH后U80→60→56；B采样全好帧，一次短暂未锁；无DOCKED、INCOMPLETE | 用户：“有转进，但更多是左轮大幅度动作，右轮基本没动。现在蓝一变到左1/3了”。4 cm/s短转使目标先靠近中心后跨过中心，未取得完整实物轮速或每个脉冲轨迹 |

以上各轮退出均完成STOP及VISION_ONLY零速清理，没有cleanup错误。第一/三轮未观察到ARM不能抹去用户在窗口外描述的动作，也不能据ACK或按钮口述补造启动时刻；第04/05轮不发合成报告或主机心跳，明确保留一次主机启动来源。

`ground_straight_e7_2s_01.jsonl`是另一次**合成居中视觉＋真实C/J3/IR/UART及注入租约**的两秒直行隔离试验，不是真实相机停靠。逻辑先+5/+5，距离低于500 mm后+3/+3；循环内J3从618到454 mm，首个清理zeroSent时436 mm、稍后430 mm，最终VISION_ONLY、未ARM、零速报文完成。用户明确说：“往前走，我看基本是直的”。它证明本条件下连续直行命令能够产生较直的前进，不证明轮速完全相等、短促起步不对称的根因或E8修复通过。上述短促纠偏与连续直行的差异，是E8尝试在接近阶段保持两轮同向连续转动的实际依据。

E8真实蓝1首轮`build/remaining_20261104/integrated_blue1_e8_01.jsonl`已完成 **DOCKED_OBSERVED**，记录116个CCTL和110个BCTL快照。由预检已锁定的蓝1开始，仅一次HOST START，采用真实相机与真实J3/IR/UART，不发送合成报告或主机心跳。首见ARM为主机2.169262秒、首见DOCKED为31.484328秒，相隔 **29.315066秒**；这是采样时刻差，不是精确内部状态切换延迟。DOCKED时J3读329 mm、U110，随后约3.18秒驻留保持未ARM、逻辑零速且zeroSent=true，通过该次板上驻留检查；退出STOP→VISION_ONLY无cleanup错误。用户原话：“持续向前，不明显偏转，左轮大概多走了1cm？探头前端距离大概33.5cm”。该反馈确认连续前进及终点约335 mm；左轮多走约1 cm是带疑问的整轮估计，不是精密轮程或每次纠偏位移。J3终态329 mm与探头前端尺距约335 mm是本次不同方法的读数，不能据约6 mm差值外推传感器精度或修改换算系数。末段对准/重确认仍耗时约25秒，机械停车时刻未单独测量。该轮未从画外开始搜索。后续蓝2红2试验与人工观察按各自记录范围列在下文，不能将其合并成六车位完整搜索→停靠验收。

E8蓝2的证据分两段保留。第一段`build/remaining_20261104/integrated_blue2_e8_red2_01.jsonl`输出 **DOCKED_OBSERVED**，保留99个CCTL、96个BCTL快照，无主机START、无合成报告、无心跳。红2事件7、新请求、重锁及ARM已记录；99个C快照全部逻辑零速、motionPermit=false，状态为82个IDLE、5个ACQUIRE、12个DOCKED，没有APPROACH。J3从约633 mm变至约295 mm后直接达到DOCKED条件。因此该观察窗口证明红2启动链和板上终态，**没有记录实际前进命令，不能计为该窗口内完成了运动停靠**；报告原结果保留，不因名称含DOCKED就补写运动。

第二段发生在上述observer结束之后：用户用KEY0复位，让红2与红1重叠，随后报告车向前走并停止，尺估终距约40 cm；手和纸张可能影响当时的距离，缺少覆盖这段动作的连续日志。事后`build/remaining_20261104/e8_blue2_after_operator_key0.json`初始读回E7070008、实体digit2、DOCKED/未ARM、L0/R0、zeroSent=true、真实J3 342 mm且蓝2锁定；B保留事件7/id2，U141、框144×159，之前框约87×97。这是新的KEY0会话，不把事件编号与前一轮串成同一序列；终态后的U和框变化也不能倒推DOCK判定当帧或精确车体位移。记录末尾已切回VISION_ONLY、未ARM、零速；随后独立恢复适用的13.6秒扫描预算。蓝2因此有**用户实物前进/停车观察和事后终态佐证**，不冒充全程遥测，不将约40 cm与342 mm相减当作精确停车误差，也不由本次数据确认是红1或某个未记录时刻导致运动。

E8蓝3实体POWER试验`build/remaining_20261104/integrated_blue3_e8_power_01.jsonl`保留 **257个CCTL、254个BCTL快照**，没有主机START、合成报告或主机心跳。首次ARM在主机61.5772666秒，首次DOCKED在77.3039882秒，采样时刻差 **15.7267216秒**；DOCKED时真实J3 321 mm，之后11个DOCKED样本跨3.127523秒均未ARM、L0/R0、zeroSent=true，再清理到VISION_ONLY，无cleanup错误。终态约80.119秒曾短读167 mm、sonarHold=true，下一80.431秒读308 mm且hold=false，全程仍保持DOCKED/未ARM，未重新行驶；不能写成整轮从未触发HOLD保护。记录12个APPROACH非零快照：逻辑5/5有2个、3/5有4个、3/4有6个，接近过程距离656→500→334 mm；未进入SEARCH。因此该轮覆盖真实相机接近、减速、差速微调、停靠及E8实体POWER启动。254个B快照全部好帧且新鲜，无候选溢出/错误，253次锁定，唯一未锁为初始新tag的ACQUIRING；末B好帧/锁定、U128。用户原话：“稳定向前，最终距离大概31cm”。约31 cm为现场估计，不把321 mm读数与该估计作为精确停车误差；本轮同样未从画外开始搜索。

E8蓝4`build/remaining_20261104/integrated_blue4_e8_host_01.jsonl`完成 **DOCKED_OBSERVED**，保留99个CCTL、93个BCTL快照；一次HOST START，无合成报告或主机心跳。首次ARM在2.1602634秒，ALIGN逻辑−3/+3、J3 655 mm；7.300秒APPROACH 5/5、642 mm，8.043秒5/3、585 mm，9.260秒4/3、487 mm，11.206秒进入ACQUIRE零速、334 mm，28.2996343秒首次DOCKED、316 mm。首见ARM到DOCKED相隔 **26.1393709秒**；近距停车、重确认与末段短转修正历时约 **17.1秒**，不能当作连续转动时长。随后11个终态样本跨3.27686秒，全部J3 316 mm、未ARM、逻辑零速、zeroSent=true；清理VISION_ONLY无错误。

该轮93个B快照来自不同帧，全部good/fresh/observed/locked，无候选错误或溢出；框从84×94到157×172，U从132经最低77到末111。未观察到HOLD、IR、LOST或SEARCH。用户原话：“启动的时候有抽动，然后偏右。直着向前接近后。停止，最后短向左修，修回居中（虽然还是有点偏右），最终停车距离大概32cm”。因此保留起步抽动、偏右和最终仍略偏右，不能说已经消除偏航，也未测出实际轮速；约32 cm是用户现场估计。

用户随后明确：“我觉得5/6都不用单独测了，1-4已经说明了性能”。据此取消本轮蓝5/6独立地面试验；六张蓝牌的静态识别和实体选择证据保留，不能改称5/6地面任务通过。随后仅沿用蓝4完成一次从画外开始的搜索→停靠试验，结果为NOT_FOUND失败，详见下文；不再逐牌扩测，后续已转入用户要求的E9有限反向回扫候选实现。

E8蓝4画外搜索`build/remaining_20261104/integrated_blue4_e8_search_01.jsonl`保留 **153个CCTL、150个BCTL快照**，由实体POWER启动，零主机START、零合成报告、零心跳。首见ARM在22.954783秒，SEARCH逻辑+4/−4；24.568753秒首次ACQUIRE时，C frame24263为observed=true但未locked，已zeroSent，累计搜索1.586529秒。26.999764秒未完成锁定而回SEARCH；31.709/34.006秒记录近距HOLD。用户移开障碍物后，41.016秒FAR恢复搜索；46.869秒累计有效SEARCH达到13.6秒，进入最终ACQUIRE，49.422秒自动进入 **NOT_FOUND/SCAN_BUDGET**、撤销ARM并归零，清理VISION_ONLY无错误。该轮没有ALIGN、APPROACH或DOCKED，**画外搜索→停靠未通过**。瞬时observed证明曾出现目标观测，不等于取得持续锁定；近距暂停时间不计入13.6秒有效搜索预算。

用户原话：“我移开了障碍物，其继续搜寻。其扫过蓝4两次，但都未锁定。是不是扫过速度太快处理不过来”。这保留了实物两次扫过未锁定、近距阻挡解除后恢复以及对速度/处理的疑问；尚未确定唯一原因，不把疑问写成已证实的吞吐瓶颈。此前蓝4预锁定目标的接近/停靠成功与本次画外搜索失败分别保留，不能互相替代。用户随后明确要求“看到后停过了，再慢速/小步回扫”，已采纳为E9候选；不新增逐牌试验，也不把尚未验证的方案写成E8失败已修复。

对该E8失败日志的只读核对不支持简单的处理吞吐断流解释：所采150个不同B帧全部frameGood/fresh，处理延迟38.819–45.892 ms、快照采集年龄39.587–84.890 ms；bufferDrop稳定为历史值3，completion discard为0，当前overflow/error/overrun/transportSticky均为0，任务期间采得C来源健康。B稀疏轮询记录149次NOT_FOUND和1次REQUEST_CHANGED，没有采中C frame24263的短暂接受，不能写成“从未识别”或声称覆盖每个原生帧。最早C zeroSent后，新采集拒绝候选的几何中心约在+303.352 ms到U155、+583.240 ms到U215并裁边、+863.128 ms到U218；此前−16.520 ms为U65。这是native y框中心，不是锁定报告坐标；reason4同时涵盖方向/锚点定向或形状拒绝，reason3为不确定。新采集画面在零速报文后仍漂移，支持扫过后未留住目标的现象，但未测出实物停稳时间，也未确定惯性、摆位和识别波动各自的贡献。

**E9 Full Compilation及post-fit PASS：**`build/member_b/20261104T171519_480274Z_build/`编译 **1218.109秒**、门检 **26.779秒**，0错误、92警告、无critical warning。ALM **29699/32070（93%）**、寄存器41206、M10K357/397、存储位2802640、DSP51/87、PLL2。四角setup/hold最差 **+0.629/+0.117 ns**，recovery/removal最差 **25.712/0.433 ns**；报告门检88项，非法/未约束项均0。每角同步链63/63覆盖PASS，MTBF仍未评估；writeGray/readGray/timeGray为9/9/32位全覆盖，resultToCamera1589位、requestCdc22位与resultToDisplay979物理端点覆盖完整。max-skew和net-delay约束最差裕量分别 **17.730 ns、11.957 ns**，这些是裕量，不是测得传播延迟。构建完成UTC **2026-11-04 17:36:05.089257**，原始SOF **6706161字节**。

原始E9 SOF实际下载成功，`program_e9_console.log`中`buildIdVerified=true`，完成UTC **2026-11-04 17:36:35.545149**（AEDT次日04:36:35）。随后保持VISION_ONLY/未ARM/零速；`e9_scan_calibrated_13600ms.json`恢复同场地适用的13.6秒预算。`e9_blue4_calibration_preflight.json`的4/4独立C/B快照健康锁定蓝4，U125、J3663–664 mm、cfg1已校色、SW3单选，无IR/HOLD且zeroSent=true。画外搜索预检另有4/4健康NOT_FOUND、J3约696 mm；预检证明准备条件，不证明搜索/回扫/停靠成功。这些文件均位于`build/remaining_20261104/`。

### E9蓝4画外搜索：发现/锁定通过，任务未完成，回扫未触发

`build/remaining_20261104/integrated_blue4_e9_search_01.jsonl`保存 **650个CCTL、84个BCTL快照**，由实体POWER启动，主机START/合成报告/主机心跳均为0。首见ARM在主机 **30.3643098秒**；本轮只设约60秒主机观察窗，观察器记录的任务观察时长为 **60.0274842秒**，随后由主机明确STOP，不能称生产120秒任务墙钟超时、SCAN_BUDGET用尽或自主DOCKED。最后 **90.445834秒**读回VISION_ONLY、未ARM、左右0、zeroSent=true、J3663 mm，`cleanupErrors=[]`。

| 观察时间（主机秒） | 板上事实与范围 |
|---|---|
| 30.3643098起 | 正常SEARCH逻辑+4/−4，累计搜索转动请求 **1.441116秒** |
| 31.971505 | 进入ACQUIRE并停车确认 |
| 32.098617 / 32.225489 | 分别采到targetObserved / targetLocked；之后scanElapsed未继续增长 |
| 81.404994 / 81.514565 | 仅两次APPROACH快照，请求+5/+5；它们不是持续前进时长或轮端位移测量 |
| 81.786688 | LOST且零速；其后返回ACQUIRE，最终仍未DOCKED |
| 观察窗结束 | 主机STOP收尾，failure仍NONE；不是自主成功停车，实机任务记 **INCOMPLETE** |

任务段442个C快照全部sourceHealthyFresh=true、J3有效，无HOLD、IR或fatal；状态采样为SEARCH10、ACQUIRE413、ALIGN16、APPROACH2、LOST1。状态样本数不等于动作次数或脉冲数。**没有反向SEARCH，E9新增回扫分支没有在本轮触发**，因此既不能写“回扫奏效”，也不能把ALIGN的反向修正称为回扫功能验证。J3在656–705 mm间变化，没有形成终端停靠距离。

全部84个B快照均fresh/good，无新增drop、候选overflow、overrun或transport故障，cfg1、red45/blue28；任务中的57个B快照为54次锁定、3次NOT_FOUND。所采U由134→142→154长时间停滞→133→119，随后短暂reason4拒识，再到69/66。它支持目标被发现后仍反复对准、越过中心的现象，不支持简单的吞吐断流结论；稀疏轮询不覆盖所有原生帧，也不能推导精确轮速或机械停止时间。

用户原话：“**停转的时候几乎正中，但是继续逆时针修后反而有点偏右边。最后顺时针反修，反而又偏左了**”。本版保留ALIGN迟缓/过冲缺陷，尚未完成画外搜索到停靠。下一版优先处理该实机问题；不重复蓝5/6测试，不将E8已见目标停靠成功或E9仿真回扫覆盖当作本轮闭环通过。

### E10：放宽居中与直接进入前进纠偏

E9已找到并锁定蓝4，但60秒观察窗内反复原地修正而未停靠，用户观察到跨过中心后再反向过冲；用户随后明确同意放宽居中要求。E10据此将默认`ALIGN_LOW/HIGH`从110/130改为 **90/150**，而不是取消目标身份、锁定或安全条件。坐标仍是原U，不改相机映射、视觉检测、拨码编号或真实J3输入。

| E10默认目标横坐标与距离 | 满足新鲜锁定及安全资格后的行为 |
|---|---|
| U90–150，距离>500 mm | 前进+5/+5 cm/s |
| U90–150，350<距离≤500 mm | 前进+3/+3 cm/s |
| U90–150，距离≤350 mm | 满足原安全条件时进入DOCKED并撤销任务授权；≤250 mm危险保护仍优先 |
| U75–89或151–165，距离>500 mm | 前进差速5/3或3/5 cm/s；生产负TURN_SIGN下低U为5/3，高U为3/5 |
| U75–89或151–165，350<距离≤500 mm | 前进差速4/3或3/4 cm/s |
| U在75–165之外，或≤350 mm且在90–150之外 | 撤销前进，走完整停车/重确认，再按原短脉冲ALIGN纠偏；不因扩大前进区域而放宽近距偏心停靠 |

`START`已有新鲜锁定目标时，或`ACQUIRE`完成完整零速UART、1.5秒驻留、新采集边界及三帧确认后，只要距离>350 mm且U75–165，就可直接APPROACH。正常搜索见到目标仍必须先停车确认，不能用一次observed绕过三帧资格。默认±30已覆盖原3 cm/s细转范围，所以默认生产分支不再为了这段误差原地细转；较大误差仍用原4 cm/s短转和20–100 ms逻辑脉宽。原110–130严格区间作为参数兼容场景保留，不能把它写成E10默认。

因此E10远距注入示例`x=80/160`分别应是同向5/3、3/5前进纠偏，350–500 mm内为4/3、3/4，不应再按两轮反向原地转来验收。`x=120`为同速前进。该解释仅对应E10及未调参E11的默认容差30；当前实验容差40时U80/160已在居中带内，会请求同速前进。历史E9仍属于旧严格居中行为。E9有限回扫、同一13.6秒扫描预算、120秒总任务限制、IR/J3/FAR、来源健康/时效、租约及所有取消条件保持。

本版保留原14帧、固定25 fps的合成像素层输入与顺序（通过真实生产感知核，并非实相机）；像素到UART回归的初始U80期望改为生产默认5/3前进，并加入禁止该段ALIGN的检查，本版实际像素→UART结果已随正式R6通过。居中范围变大是用户接受的行为取舍，不是已测横向停车精度或机械不对称修复。当前定向控制回归、正式R6、Full Compilation/post-fit及下载身份均已独立PASS，实际画外搜索结果为NOT_FOUND/SCAN_BUDGET，短暂APPROACH后失锁重搜，未完成停靠；详情单列。

**E10定向控制回归PASS：**`build/remaining_20261104/control_e10_20261104T175106Z/result.json`记录一次ModelSim编译与三个配置全部通过，0错误/0警告，总 **29.1663517秒**，无失败尝试。默认U90–150的生产`TURN_SIGN=-1`和泛型`+1`各 **804检查/275条完整UART**，每种spin113、drive41、zero121；细转fineLow/fineHigh均0符合新容差，前进差速steerLow12/steerHigh10、fineSteerLow2/fineSteerHigh2仍实际覆盖。另一次显式旧U110–130、负sign兼容配置 **817检查/278条UART**，其中fineLow8/fineHigh3证明旧参数的细转路径仍可用。默认、正负符号和旧参数不是三个独立产品功能总数，不把检查数相加冒充独立需求。`commands.json`及negative/positive/legacy_band日志保留在同目录。

该结果验证新默认边界、直接APPROACH及保留的安全/回扫逻辑，不证明机械停稳、轮速或停靠精度。生产源码与TB已冻结；正式R6已独立PASS271.31444秒，`build/member_b/20261104T175030_045504Z_build/`的Full Compilation/post-fit随后也已PASS，并完成E10实际下载；实物结果另列。

**E10正式R6独立PASS：**`build/member_b/20261104T175201_822030Z_verilator_course/result.json`记录单次完整运行 **271.31444秒、退出0、13项PASS＋故意破坏锁定的mutation CAUGHT、targetMet=true、cleanBuild=true**，满足285秒目标。Verilator5.050，本轮61个新源文件、编译jobs4、最大同时2个模拟；没有复用E9的耗时或仿真结论。生产默认控制在该完整套件中再次实际通过804检查/275条完整UART。

同次`tb_pixel_uart_repair/simulation.log`保留 **14帧/14报告、固定25 fps**，像素层场景经过实际生产perceptionCore、C控制器和串行UART；输入是合成标牌像素，不是现场相机录像，也未以强制内部observed代替识别。输出计数为search41、leftCorrection18、forward79、rightCorrection34、zero116、leftSpin/rightSpin均0。初始U80的5/3前进以及U160的3/5前进差速均符合新默认入口；coarseLeft18/coarseRight34，fineLeft/fineRight均0。本像素场景没有证明近距4/3组合，后者由控制专项覆盖；UART消息与状态断言不等于车轮实测。这些是本版RTL_SIM结果，Full Compilation/post-fit及实际E10下载随后已PASS，零速校色预检完成；本轮实物搜索停靠最终NOT_FOUND/SCAN_BUDGET，失败与用户观察单列。

### E10独立完整构建、下载与零速校色

`build/member_b/20261104T175030_045504Z_build/result.json`最终 **PASS**：Full Compilation **1260.493秒**、独立post-fit门检 **25.832秒**，0错误、92警告、0 critical warning；63个构建源文件与当前冻结源码核对一致。器件使用 **29249/32070 ALM（91%）**、40840寄存器、357/397 M10K、2802640存储位、51/87 DSP、2/6 PLL。四角16项setup/hold/recovery/removal检查最差分别 **+0.909/+0.118/+26.947/+0.401 ns**；报告门检88项，非法及所有未约束计数均0。四角同步链各63/63覆盖PASS，MTBF仍未评估。writeGray/readGray/timeGray为9/9/32位全覆盖；resultToCamera1588、requestCdc22及resultToDisplay979物理端点完整覆盖。max-skew/net-delay最差约束裕量分别18.498/13.844 ns；它们是裕量，不是实测传播延迟。

构建完成UTC **2026-11-04 18:11:56.936771**。原始SOF位于该构建目录的`source/quartus/output_files/PartBDebug.sof`，**6706157字节**；`build/remaining_20261104/program_e10_console.log`记录实际program与E7070010身份读回 **PASS**，完成UTC **18:12:33.831751**（AEDT次日05:12:33.831751）。这来自E10自己的构建及下载，不是借用E9 SOF或时序结果。

下载后切至VISION_ONLY、未ARM、零速，并明确恢复同一适用场地的13.6秒扫描预算。`e10_blue4_calibration_preflight.json`中4/4独立C/B样本均健康且锁定蓝4，U121、真实J3约642 mm、cfg1、红49/蓝28，保持零速。该零速校色预检证明可进入下一轮观察，不证明车体实际搜索、纠偏或停靠；随后画外蓝4实体POWER试验进入短暂APPROACH后失锁重搜，最终NOT_FOUND/SCAN_BUDGET，未停靠，详情单列。上述运行日志位于`build/remaining_20261104/`，不自动成为仓库内完整日志包。

### E10蓝4画外实机：短暂进入接近后失锁，搜索预算耗尽

`build/remaining_20261104/integrated_blue4_e10_search_01.jsonl`与`e10_operator_notes.json`记录真实相机、真实J3/IR/UART、同一塑胶地面及底盘供电；实体POWER启动，主机START、合成写入、主机心跳均为0。共 **370个CCTL、43个BCTL快照**，观察器记录任务时长 **22.2096082秒**，结果 **NOT_FOUND_OBSERVED / SCAN_BUDGET**，不是DOCKED或成功搜索停靠。

| 主机观察时间（秒） | 实际记录 |
|---|---|
| 24.5707036 | 首次ARM、SEARCH正常+4/−4 |
| 26.292697 | 搜到蓝4后ACQUIRE停车确认，随后记录居中U121及锁定 |
| 27.843132 | 短暂APPROACH，左右请求+5/+5，证明本轮进入了E10直接前进路径 |
| 27.952800 | 失锁转LOST并撤销前进 |
| 28.253924 | 约300 ms后重新进入正常方向SEARCH |
| 29.909043起 | 后续采到U179/201边缘目标及ALIGN，又丢失标牌；相反轮向的命令属于ALIGN，不是反向SEARCH回扫 |
| 46.7802808 | SCAN_BUDGET耗尽13.6秒累计搜索预算，NOT_FOUND、未ARM、零速发送完成；最终J3为450 mm |

全部任务C样本来源健康，43个B帧均good/fresh，B处理延迟 **38.818–48.436 ms**，未见本轮传输或候选故障。没有DOCK，也没有反向SEARCH；E9加入的有限回扫在本轮仍未触发，不能声称其物理效果通过。J3450 mm是终态测距，不是合格停靠距离或尺量精度。轮询只给出采样状态，短暂APPROACH不等于测得持续运动时长或位移，也不以好帧/健康来源排除目标身份或几何暂时失效。

用户原话：“**搜到后停止了，此时蓝四在正中。随后又重新开始搜索，再一次掠过蓝四后停止**”。后续确认短暂前进再转离、纸板一直固定、两轮最终已经停止。清理回VISION_ONLY、未ARM、左右0、zeroSent=true，`cleanupErrors=[]`。因此E10已验证放宽居中可进入前进路径，但**失锁后恢复搜寻导致再次掠过目标的问题仍在，画外搜索停靠未通过**。本次发布完整保留该失败；后续修正另行验证。

### E11：失锁后完整停车重确认与调参接口验证

E10曾在U121短暂进入APPROACH，随后LOST约300 ms即回SEARCH，固定目标再次掠过且未停靠。E11将LOST等待结束后的出口统一改为ACQUIRE，无论此时是否为健康NOT_FOUND，都先完成零速UART、1.5秒驻留、新采集边界及三帧确认，再决定接近、对准或继续搜索。`stationaryRecoveryRequired`保留该停车确认义务，跨HOLD和来源中断仍有效，包括丢牌与HOLD同一周期发生；一旦该义务已建立，就不能因安全恢复或暂时无目标跳过确认。普通跟踪失锁不新授予E9反向回扫资格，同一搜索预算、已用回扫次数及120秒任务计时不重置。这是针对真实失败的修正实现，已通过独立控制验证并下载；后续实机已采到预算未耗尽时的LOST→ACQUIRE，但抽动与过冲仍在，未完成画外搜索停靠。

该新义务仅在ALIGN/APPROACH失效时建立，包括失效与HOLD同周期发生。若目标仍有效时先进入HOLD，随后才在HOLD内丢牌，则沿用旧分支：障碍和来源条件恢复后，健康NOT_FOUND仍可能直接回SEARCH。这个先HOLD、后丢牌的顺序没有纳入本轮修复，保留为已知边界，不称全部HOLD恢复都已强制停车确认。

调参端点独立聚焦记录为`build/remaining_20261104/tuning_e11_20261104T182254Z/result.json`：ModelSim **128检查/20报告PASS，1.5052586秒，0错误/0警告**。主机测试`build/remaining_20261104/tuning_e11_host_tests.log`为 **18测试PASS，0.155秒**；实际生产Tcl脚本配mock传输测试`tuning_e11_tcl_tests.log`为 **2测试PASS，0.938秒**。Tcl结果验证脚本协议检查及设计族识别，没有使用实物USB-Blaster，不是实机调参或JTAG运动验证。

E7070011冻结源码已通过独立主控制定向、正式R6最终轮、Full Compilation/post-fit与实际下载，停车调参也已获得真实JTAG读回证据；地面首轮及search3搜索均NOT_FOUND，三个短时对照均INCOMPLETE；发布保留全部失败，未完成画外搜索停靠。保持用户取消蓝5/6单独地面测试的范围，不用旧版停靠成功覆盖E11的新行为。

### E11独立控制验证、R6失败与调度修正

控制定向最终记录`build/remaining_20261104/control_e11_20261104T182830Z/result.json`为 **PASS，34.258085秒**，一次ModelSim编译、三个配置，0错误/0警告。runtime开启的生产负sign和泛型正sign各 **996检查/358条完整UART**，其中runtime专属28条；runtime关闭、旧110–130严格参数且tuning输入为X的兼容配置 **847检查/289 UART**。覆盖持续NOT_FOUND下LOST仍必须ACQUIRE、失锁与HOLD同周期、来源中断后重新驻留、确认超时才恢复SEARCH、STOP取消，以及五项调参边界、75–165前进范围、fine+1差速和非法参数零运动门控。配置检查数不相加冒充独立功能数。

前置`control_e11_20261104T182549Z`因TB末尾打印参数不足失败，`182629Z`及diagnostic因期望串中`%s`空正号多产生空格失败；实际UART内容正确，修正只涉及TB格式，不是生产RTL功能失败。原失败日志保留，不能写成“没有失败尝试”；最终通过来自上述单独完整运行。

第一次正式R6 `build/member_b/20261104T182917_566351Z_verilator_course/result.json`为 **FAIL，302.015209秒、退出1、targetMet=false**。13个正常场景均PASS，但最后故意坏锁定mutant的编译达到300秒总期限，未得到CAUGHT，不能将此轮标为完整通过。随后仅优化`tools/lib/verilator_suite.py`调度：首对长仿真运行期间，主线程按顺序预编译后续场景；始终最多两个仿真、一个编译进程、jobs4及原300秒总期限。保留本次fresh源码/精确输入哈希缓存，已准备二进制使用前再次核对字节；未删场景、帧数或断言，也不复用往轮二进制。

runner最终 **18项HOST_RUNNER测试PASS，1.962秒**，日志`r6_e11_overlap_host_tests_final.log`；最初sandbox临时目录WinError5及先前native通过日志保留，不混为RTL失败。全新第二轮`build/member_b/20261104T184126_548104Z_verilator_course/result.json`独立 **PASS，219.199994秒、退出0、13 PASS＋mutation CAUGHT、cleanBuild=true、targetMet=true**，61个新源文件、11个场景预编译，仍单编译/最多2模拟。此实测满足285秒目标，首轮失败未覆盖；生产RTL冻结不因runner调度修改而改变。

### E11完整构建、实际下载与停车调参实测

`build/member_b/20261104T182211_444905Z_build/result.json`最终 **PASS**：Full Compilation **1375.853秒**、post-fit门检 **26.278秒**，0错误、92警告、0 critical。ALM **29403/32070（92%）**、寄存器41147、M10K357/397、存储位2802640、DSP51/87、PLL2/6。四角setup/hold/recovery/removal最差分别 **+0.237/+0.120/+26.616/+0.471 ns**；报告门检88项、非法及未约束项0，同步链每角63/63覆盖PASS、MTBF未评估。Gray写/读/时间9/9/32位覆盖；resultToCamera1589、requestCdc22、resultToDisplay979物理端点覆盖完整；max-skew/net-delay约束最差裕量18.670/12.457 ns，不是实测传播时间。

构建完成UTC **2026-11-04 18:45:34.129044**；原始SOF为该目录`source/quartus/output_files/PartBDebug.sof`，**6706153字节**。`program_e11_console.log`记录实际编程及E7070011读回 **PASS**，完成UTC **18:46:11.345908**（AEDT次日05:46:11.345908）。本版成功与E10时序/原产物分开，旧失败不改写。

`build/remaining_20261104/e11_tuning_hardware.json`为 **真实JTAG停车调参PASS**，不是合成传输测试。整个序列VISION_ONLY、未ARM、无运动许可、左右0、zeroSent=true，START/合成写入/心跳均0：

| 实际步骤 | 独立读回与范围 |
|---|---|
| 初始默认 | search/turn/approach/fine/tolerance = 4/4/5/3/30，A1能力可读 |
| 恢复已验证的search4基准 | 同塑胶地面原三圈13.6秒，scanCalibrated=true |
| 写turn3、approach6、fine4、tolerance35 | 得到4/3/6/4/35，另一次独立读回一致，search未变所以扫描标定保留 |
| 写search3 | 得到3/3/6/4/35，scanCalibrated=false；没有以3 cm/s启动车辆或测转圈 |
| 恢复默认 | 读回4/4/5/3/30，但scanCalibrated仍false，默认恢复不会自动恢复资格 |
| 恢复原search4标定记录并收尾 | 显式恢复同场地既有13.6秒基准，最终STOP、未ARM、零速；不是替search3建立标定 |

该实测证明参数写入、保持、读回、能力及标定失效行为；没有在调整后的速度下运动，不证明实测速度、稳定性或停靠效果。`e11_blue4_calibration_preflight.json`的4/4独立C/B样本健康锁定蓝4，U116、J3约660 mm、cfg1已校色，全部调参默认且scanCalibrated=true，保持零速。后续画外搜索与短时对照的失败结果另列；运行日志位于`build/remaining_20261104/`。

### E11同一固件的地面试验与会话调参

用户明确要求不再生成新版本，本段始终使用同一 **E7070011** 生产RTL和已通过构建的SOF，仅通过停车`tune`与`scan`改变会话参数，没有另做RTL修复或用新编译覆盖旧失败。固件复位默认仍为 **search/turn/approach/fine/tolerance = 4/4/5/3/30**。本段最新实验设置为 **3/5/4/3/40**，即search3、turn5、approach4、fine3、容差±40（U80–160），扫描预算 **15.1秒**；该配置是volatile现场设置，KEY0/掉电/重下载后不会保留。turn5（当时approach5）已观察到动作但仍过冲/INCOMPLETE；approach4同场景也已INCOMPLETE，降速未消除抽动/过冲；本轮停止追加测试。

**首次地面搜索未通过。** `integrated_blue4_e11_search_01.jsonl`记录368个CCTL、50个BCTL快照，实体POWER、0主机START/合成写入/心跳；观察器任务时长 **28.0071143秒**，终态 **NOT_FOUND/SCAN_BUDGET**，清理至VISION_ONLY、未ARM、zeroSent、J3398 mm。C轮询直接采到两次reverse SEARCH（−4,+4）；另一次149999 μs扫描计数增量与第三个短步相符，但这是推断，不是第三步完整波形或机械回转测量。用户看到停后仍逆时针，未观察到回调，故仅能确认反向命令出现，不能说机械回扫奏效。本轮未进入ALIGN、APPROACH或LOST，尚未实机触发LOST修正。

该轮50个B帧均fresh/good，cfg1红45/蓝24，与E10配置不同；采样中候选位于边缘或发生方向拒识，没有B accepted targetU。C第二次短暂observed/locked与B稀疏轮询未采中并不矛盾，不能据此说从未识别、每帧都锁定或已证实处理吞吐不足。用户停后把车复原，后续场景应各自记录。

**search3转圈计时及15.1秒依据。** 修改search4→3后scanCalibrated确实清除。计时使用CHASSIS_INJECT的合成健康无目标报告，经真实控制/J3/IR/UART驱动落地底盘，由用户按A停止；这些是地面转动观察，不是实相机搜牌任务。下表时间是停止时FPGA累计获准SEARCH请求时间，不是航向传感器或独立机械停稳计时，包含人工按键反应影响：

| 原始记录（均在build/remaining_20261104） | 累计SEARCH时间 | 用户观察及结论 |
|---|---|---|
| `ground_e11_search3_circle1.jsonl` | **30.014554秒** | 实际两圈再多约10°，后退约3 cm；不能写成一个单圈。除2得到15.007277秒仅作每圈平均参考 |
| `ground_e11_search3_circle2.jsonl` | 无有效转圈时间 | IR未解除，2个状态样本、无运动，**TRIAL_INVALID**，保留失败，不计入有效圈数 |
| `ground_e11_search3_circle2_retry.jsonl` | **14.093147秒** | 一圈约多7.5°，右轮多走约1 cm |
| `ground_e11_search3_circle3.jsonl` | **14.691960秒** | 一圈约多3°，后退约4 cm |

根据**两次单圈和一次双圈参考**写入保守15.1秒有界预算，`e11_search3_scan_15100ms.json`保存结果。不能称三次精确单圈标定、精准360°或已经量得自动停车角误差。原13.6秒属于search4条件，不能套给search3；当前15.1秒也不能在复位回search4后盲目沿用。反向回扫同样消耗该总预算，净向前转角不等于总累计命令时间；实验室环氧地面仍未验证。

**慢速搜索仍未停靠。** `integrated_blue4_e11_search3_02.jsonl`记录 **593 C/69 B、43.5151717秒任务观察、NOT_FOUND/SCAN_BUDGET**，实体POWER、无主机START/合成/心跳，cleanupErrors为空。用户描述首圈漏牌、第二圈发现，回修时只有右轮动作且过冲；该“首圈/第二圈”保留为用户描述，不转写为精确转角或两个经过计时的完整圈。日志观察到三段LOST→ACQUIRE→ALIGN，但全在预算耗尽后，旧budgetDone分支也会这样恢复，不能单凭该轮证明新LOST修复。它更不等于已消除机械过冲或完成停靠；不以稀疏快照补造轮速或动作时长。

**低转速隔离检查未完成对准。** `integrated_blue4_e11_turn3_15s.jsonl`使用search3、turn3、approach5、fine3、tolerance40，记录 **273 C/35 B**，15秒观察上限、实际taskObservationSeconds **15.1179462**，最终 **INCOMPLETE**，host STOP后零速清理且cleanupErrors为空。蓝4 U约40→41，用户只看到抽动，没有取得有效对准。随后turn5试验仍用同一固件及 **3/5/5/3/40**，实际结果另列；参数写入成功不替代机械效果。

### E11 turn5同场景对照：能够转动，但仍过冲

`integrated_blue4_e11_turn5_15s.jsonl`在同一固件、search3/turn5/approach5/fine3/tolerance40下完成 **340 C/44 B**、taskObservationSeconds **15.002259秒**，结果 **INCOMPLETE**。结束由15秒主机观察期限收尾，cleanupErrors为空，最终VISION_ONLY、未ARM、左右0、zeroSent、J3596 mm；没有完成搜索停靠，也不是生产120秒任务限到期。

目标U由41→44→50→53→82；主机37.748570–38.379696秒采到APPROACH +5/+5，38.501820秒为LOST/0/0，38.813秒进入ACQUIRE，40.472秒为ALIGN −5/+5。B在38.983秒已采到U195，随后197/198，目标再次到右边缘。**整个观察中scanRemaining均为15100000 μs**，所以本轮在扫描预算未耗尽时实际出现LOST→ACQUIRE，而非直接回SEARCH，是E11新增恢复路径的板上证据；该状态顺序不证明车身已机械停稳，也没有消除越过中心或失锁。

用户原话：“**最开始右轮短抽，然后动了一下几乎回正，然后又在右偏（两侧轮子都有动作），然后4到了右侧边缘，随后左轮抽动，或是因为超时而停止。整体是由前进一些距离的**”。较turn3只有抽动，本轮用户确实看到双轮动作与一段前进，但对准/接近仍未完成；不能把这一观察写成轮速匹配、稳定对准或成功停靠。

此前`search3_02`的三段LOST→ACQUIRE→ALIGN均发生在扫描预算耗尽后，旧budgetDone路径也会进入ACQUIRE，**不能单独用那轮证明本次LOST修复**；本轮未耗尽预算的序列提供了不同范围的证据。

接着只通过停车调参将approach5降至4，最新会话参数为 **3/5/4/3/40**，15.1秒预算保留；默认仍4/4/5/3/30、生产RTL及E7070011不变。随后的15秒对照也已INCOMPLETE，详情见下一节；减速未解决本轮过冲。

### E11最后一轮approach4：减速未消除抽动和过冲，停止追加测试

`integrated_blue4_e11_turn5_approach4_15s.jsonl`使用同一E7070011及 **search3/turn5/approach4/fine3/tolerance40**，保留 **289个CCTL、36个BCTL快照**，实体POWER、0主机START/合成写入/心跳。15秒主机观察期限下，taskObservationSeconds为 **15.0186774秒**，结果 **INCOMPLETE**；cleanupErrors为空，最终VISION_ONLY、未ARM、左右0、zeroSent=true、J3619 mm。没有DOCKED，不能把主机到限收尾写成自主停靠完成或120秒任务期限触发。

蓝4在U41停留多个采样周期，随后43→46→49→126→140，再变为NOT_FOUND。主机36.730秒采到APPROACH +4/+4，37.366秒为ACQUIRE。用户原话：“**最开始两轮一起往前抽动，随后右轮抽了波大的，让蓝四几乎居中，然后又抽了波大的，导致蓝四有些超出右边缘**”。降低前进请求速度没有在本轮解决短转起步不均、抽动或过冲；不据局部坐标改变推算实际轮速、位移或精确转角。

| 本版真实相机地面轮次 | 任务观察时长 | 实际终态 |
|---|---:|---|
| 原search4/默认参数搜索 | 28.0071143秒 | NOT_FOUND/SCAN_BUDGET；直接采到反向SEARCH命令，机械回扫效果未确认 |
| search3、15.1秒预算搜索 | 43.5151717秒 | NOT_FOUND/SCAN_BUDGET；预算耗尽后的LOST→ACQUIRE不单独证明新修复 |
| turn3、approach5、tolerance40隔离 | 15.1179462秒 | INCOMPLETE，只有抽动，未有效对准 |
| turn5、approach5、tolerance40隔离 | 15.002259秒 | INCOMPLETE；未耗尽预算下LOST→ACQUIRE有板上证据，仍过冲失锁 |
| turn5、approach4、tolerance40隔离 | 15.0186774秒 | INCOMPLETE，降速仍抽动并越过目标 |

本轮到此停止追加测试，未增加RTL修改、编译或新版本。最终维持E7070011、VISION_ONLY、未ARM、零速；会话实验参数 **3/5/4/3/40、15.1秒**暂时保留，**只是已试组合，不是经过验证的推荐配置**。固件默认仍 **4/4/5/3/30**，KEY0/掉电/重下载恢复默认并丢失运行时扫描标定。停车调参与标定失效链已实机通过，LOST恢复路径有特定条件的板上证据；机械过冲、持续捕获和外视野搜索到停靠仍未通过。E8蓝1/3/4从已见目标停靠的历史成功保留，不能作为本版完整任务通过。

### E12独立控制回归与保留的失败尝试

首次控制定向目录`build/remaining_20261104/control_e12_20261104T192836_046724Z/`保留为失败尝试：runtime分支调整后，TB仍引用旧层次名；生产源码未因此改变，修复只涉及TB引用。随后一次编译、三配置完整运行`build/remaining_20261104/control_e12_20261104T192902_661125Z/result.json`独立**PASS，44.0894113秒、0 errors/0 warnings**：runtime两种TURN_SIGN各**2041检查/500完整UART**；关闭runtime且timing输入未知的legacy参数配置**848检查/289 UART**。原失败不覆盖，逻辑计时及完整UART检查不等于真实电机速度阶段或机械停稳验证。正式R6结果见下文；完整构建/post-fit、下载与实机结果继续分别记录。

### E12正式R6首次完整运行通过

`build/member_b/20261104T193009_881634Z_verilator_course/result.json`独立**PASS，223.404755秒、exit0、targetMet=true，13项PASS及mutation CAUGHT**。本版首次正式R6即达到285秒目标；61个fresh源文件，jobs4、最多2个仿真与1个编译进程，11项预编译，继续沿用E11经验证的当前调用精确输入/产物检查及调度策略。没有减少场景、输入帧数或断言，也没有借旧版结果填补本版证据。此前E11的302.015209秒FAIL仍是历史失败，未被这次E12成功覆盖。

此前综合于悉尼时间2026-11-05 06:32:15完成、DSP51；随后完整构建/post-fit、下载及静止验收也已取得下述独立PASS。R6通过本身不证明实物起步同步或搜索停靠成功。

### E12完整构建、实际下载与停车pulse参数验证

`build/member_b/20261104T192605_706632Z_build/result.json`为**PASS**：Full Compilation **1163.903秒**，post-fit gate **26.783秒**，0 errors、92 warnings、0 critical warnings。最终资源为**29647/32070 ALM（92%）**、41286寄存器、357/397 M10K、2802640存储位、51/87 DSP、2/6 PLL。四角16项setup/hold/recovery/removal最差裕量为**+0.842/+0.102/+28.060/+0.434 ns**。88项report gate通过，illegal/unconstrained均0；每角同步链63/63覆盖，MTBF仍NOT_ASSESSED。Gray覆盖9/9/32，resultToCamera1589、requestCdc22及resultToDisplay979的对应物理覆盖完整；maxSkew/netDelay最差约束裕量18.127/14.470 ns，并非实际传播延迟。

构建于**2026-11-04 19:45:56.942735 UTC**完成；原始`source/quartus/output_files/PartBDebug.sof`为**6706156字节**。`e12_production_source_match.json`记录63个生产源文件与本次构建副本逐字节一致，后续没有用其他源码替换产物。`program_e12_console.log`记录实际下载、读回**E7070012 PASS**，完成**19:46:26.577567 UTC（悉尼次日06:46:26.577567）**。这是本版独立结果，不沿用E11产物或时序。

`build/remaining_20261104/e12_pulse_hardware.json`为**真实JTAG静止参数PASS**，五个样本和最终cleanup均保持VISION_ONLY、未ARM、无运动许可、左右0、zeroSent=true；START/synthetic/heartbeat计数均0，cleanupErrors为空。

| 静止操作 | 独立状态/范围 |
|---|---|
| 默认读取 | pulse min/max/kickMs/kickSpeed为20/100/0/5；tune仍4/4/5/3/30 |
| 写入首个分段配置 | pulse100/200/60/5，即总100–200 ms、起步60 ms/5 cm/s请求 |
| 独立再次读取 | 四项与请求完全相同；五项tune及扫描状态未变 |
| 边界值写入 | pulse300/300/100/8，只在停车V1写入/读回，**没有按此速度运动** |
| 恢复默认及cleanup | pulse20/100/0/5，tune保持默认，扫描仍未标定；停车/zeroSent确认 |

这只证明真实传输、整组保持、读回和字段互不影响，不证明UART速度请求产生了对应轮速、起步力或机械阶段。`e12_blue4_calibration_preflight.json`四个独立C/B健康锁定样本为U113、J3约655–659 mm、cfg1已校色；该过程零速。

随后`e12_first_profile_config.json`在停车边界写入首轮实验**tune search3/turn3/approach5/fine3/tolerance40**与**pulse min100/max200/kickMs60/kickSpeed5**，恢复同一塑胶地面search3已有15.1秒扫描记录，最终scanCalibrated=true、V1未ARM/零速。该基准仍只有E11两次单圈加一次双圈参考，未因重新写入而成为精确360°标定。首轮15秒短转比较已完成但INCOMPLETE，用户反馈略好且仍偏右；不能声称已解决单侧起转、静摩擦或过冲，详细证据见后续记录。

### E12首轮地面短转：用户反馈略好，仍偏右且未完成

`build/remaining_20261104/integrated_blue4_e12_kick5_cruise3_15s.jsonl`使用**tune3/3/5/3/40、pulse100/200/60/5、15.1秒扫描预算**，记录**320个CCTL和42个BCTL样本**。15秒观察窗实际taskObservationSeconds为**15.0223777秒**，终态**INCOMPLETE**，未DOCK；主机收尾后VISION_ONLY、未ARM、无permit、左右0、zeroSent=true、UART空闲、J3约659 mm，cleanupErrors为空。此观察窗结束不是产品120秒任务超时，也不是自动完成停靠。

用户原话：**“会好一点，但是转出来蓝色偏右一些”**。初始蓝4为U55、框左边界14且完整；BCTL采到U55→76→83→168→175。直接读到了ALIGN的`+3/−3`以及反向ALIGN的`−5/+5`命令，但没有在**同一次脉冲**内完整采到5→3转序，因此只能结合既有RTL逻辑验证与这些离散命令读数，不能宣称本轮完整机械两段过程已被采证。主要坐标偏移跨越APPROACH5/3→LOST停车，发生在反向ALIGN之前，不把整段目标位移都归因于反向短转。

任务采样中的来源一直健康，没有HOLD/IR/fatal；42个B样本均fresh/good。此范围内没有证据支持来源失效是本轮偏移的原因，但稀疏采样不能还原所有轮速、转角或机械停止时间。操作者主观“好一点”与末段仍偏右同时保留；本轮不算稳定对准或画外搜索停靠通过。

后续只将**fine3改为4**，其他保持，形成同一E12的第二轮实验**tune3/3/5/4/40**、pulse100/200/60/5及15.1秒扫描预算。此修改使远距差速慢轮变4，350–500 mm近距直行也变4、近距差速快轮为5；不是仅对一个动作单独改变速度。没有新增RTL、重新编译或新版本。第二轮结果及后续独立对照见下文，不用首轮反馈推定其效果。

### E12第二至四轮：命令两段转序与有限回正证据

各轮保持E7070012和原安全链，只在V1停车时修改一项参数，没有增加RTL版本或重新编译。C/B数量为离散JTAG快照数量，不是原生相机帧数或机械速度采样率。

| 试验 / 日志 | 相对前轮修改 | 样本与观察时长 | 实际结论与清理 |
|---|---|---|---|
| 第二轮 `integrated_blue4_e12_fine4_15s.jsonl` | fine3→4；tune3/3/5/4/40，pulse100/200/60/5 | 422C/35B，15.0445792秒 | INCOMPLETE，cleanupErrors为空，末V1零速/zeroSent、J3约636 mm |
| 第三轮 `integrated_blue4_e12_kick6_reverse_15s.jsonl` | 仅kickSpeed5→6，其他不变 | 500C/39B，15.0423456秒 | INCOMPLETE，U187→181、末J3约632 mm；未完全回正 |
| 第四轮 `integrated_blue4_e12_kick6_total200_reverse_15s.jsonl` | 仅minMs100→200，maxMs仍200：名义总时长固定200 ms，kick6/60 ms、后段turn3 | 780C/60B，任务3.8547528秒 | ALIGN_CORRIDOR_OBSERVED；首次采到APPROACH5/5便由主机STOP主动终止诊断，末V1零速/zeroSent、J3约591 mm，cleanupErrors为空；非DOCK |

**第二轮采到了板上两阶段命令转序，但没有单独验证fine4差速纠偏。** 直接采到6组同一次ALIGN的5→3速度幅值变化，正反方向各3组，后续均归零；这是命令序列证据，不是实际轮速、同步起转或机械脉宽测量。B位置U49→71→153（第三次短转后、APPROACH之前）→159→178，反向短转后188。实际APPROACH只采到5/5，未采到5/4；因此首轮怀疑前进差速造成偏移的解释未得到本轮支持，不能写成已确定原因或fine4纠偏有效。用户原话：“最开始那几下右轮抽能明显让车子转一点点，但是最后大动又使得蓝四偏右”。

**第三轮提升kick仍不足以回正。** 在原右侧U187附近保持摆位，kick升至6后，用户反馈“左轮短抽几次有效果，但未能完全回正”；B仅U187→181，仍INCOMPLETE。此反馈证明观察到有限运动，不证明设定6 cm/s对应实际轮速，也不支持已经解决静摩擦或步幅不均。

**第四轮延长总时长后，用户接受残余偏差。** 直接采到2段`−6/+6 → −3/+3 → 0/0`，B为U181→171→104/105。全部来源样本健康，B均good/fresh，无HOLD/IR/fatal/transport fault，15.1秒扫描预算未消耗。用户反馈：“几乎回正了，但是有点点偏左，不过勉强可以接受”。保留其接受误差的决定，不再把“精确居中”作为该轮必须继续追求的目标；步幅不均仍是限制。诊断helper因预设“首次APPROACH就STOP”返回exit1，并不代表失控或无效日志；`ALIGN_CORRIDOR_OBSERVED`只表示进入接近通道，不能写为DOCK或完整搜索停靠通过。

随后`e12_approach_after_alignment_preflight.json`另取得**3/3健康锁定、U84、J3约582 mm**。这是不同预检时点，不与第四轮末U104/105混为同一个物理状态，也不能假定间隔内场景完全未变。接下来`integrated_blue4_e12_approach_after_alignment.jsonl`使用同一配置**tune3/3/5/4/40、pulse200/200/60/6、扫描15.1秒**，从已经可见的目标进行最多60秒接近观察；该轮实际INCOMPLETE结果见下文；它也不属于从画外开始的完整搜索验收。

### E12第五轮接近未完成：边缘丢牌、重新搜索与近障HOLD

`build/remaining_20261104/integrated_blue4_e12_approach_after_alignment.jsonl`沿用**tune3/3/5/4/40、pulse200/200/60/6、15.1秒扫描预算**，从已见目标进行接近观察，保留**687C/85B**。taskObservationSeconds **60.0399573秒**，结果**INCOMPLETE**；cleanupErrors为空，最终VISION_ONLY、未ARM、左右0、zeroSent=true、J3约254 mm，**sonarHold仍true**。没有DOCKED，也没有用主机收尾冒充自主停靠。

板上采到5段短APPROACH，包括一次5/4请求，以及5/5、4/4；其间反复ALIGN，未形成用户可见的稳定直行加小差速过程。用户原话：“一直左右校准方式前进，并没有直行然后小差速纠偏之类操作。然后在一次纠偏过了后360度重扫的时候，没有重新抓回蓝四”。其中“360度重扫”保留为操作者描述，没有航向传感器或独立角度计量，不转写成已测精确一圈。日志对应目标触边拒识后两段SEARCH仍未找回。

J3在**248 mm**时触发近障HOLD，最小样本**240 mm**；48个HOLD样本处于**240–254 mm**，未达到≥300 mm的连续新安全样本恢复条件，因此本轮没有HOLD释放证据。最终近障保护停车不等于350 mm正常停靠，254 mm也不是合格停靠距离或尺量精度。

全部已采来源状态健康，85个B样本good/fresh，未见transport fault；蓝色候选抵达边界0/239时出现拒识码4/5。末现场真实抓图`capture20261104T200809_077960Z_capture`通过fresh及CRC检查，显示牌在图边裁切。**这只是最后现场图，不是首次失锁帧**；它与边缘拒识相符，但不还原整个失锁过程、不能单凭末图确定所有过冲原因。已经取得的5→3或6→3板上命令序证据仍不等于实际轮速或两轮起步完全一致。

| E12本次发布保留的地面观察 | 结果 | 验收范围 |
|---|---|---|
| kick5/turn3首轮 | INCOMPLETE15.0223777秒 | 用户略好但偏右；同脉冲完整5→3未采到 |
| fine4第二轮 | INCOMPLETE15.0445792秒 | 6组同次5→3命令序；没有采到5/4，不能独立确认fine4纠偏效果 |
| kick6第三轮 | INCOMPLETE15.0423456秒 | 左轮短抽有有限作用，未完全回正 |
| 总200 ms第四轮 | ALIGN_CORRIDOR_OBSERVED，3.8547528秒 | 2组6→3→零命令，用户接受轻微偏左；首次APPROACH主机STOP，非DOCK |
| 已见目标接近第五轮 | INCOMPLETE60.0399573秒 | 短APPROACH/反复ALIGN/边缘丢牌/重搜未找回，最终近障HOLD；停靠未通过 |

发布记录以这五轮为界。随后只有**tolerance40→30**改变，形成**tune3/3/5/4/30、pulse200/200/60/6**的同版本独立诊断，扫描仍15.1秒；其结果在本次快照中**待验证**，不把它写成改进已通过或推荐设置。该调参不新增RTL、编译或固件版本。SOF的复位默认仍是**tune4/4/5/3/30、pulse20/100/0/5**；KEY0、掉电或重新下载不会保留实验配置与扫描标定。原E8已见目标停靠及所有历史失败继续按各自版本保留，不能覆盖本轮未完成的主线功能。

## 已知限制与未验证范围

- E12第五轮仍反复对准并边缘丢牌，重搜未找回后进入J3近障HOLD；未DOCK。有限回正获得用户接受，命令两段转序已有实板证据，但不代表轮速一致或主线通过。随后tol30仅属独立待验实验。

- E11首轮与search3搜索均NOT_FOUND，turn3/turn5隔离均INCOMPLETE；turn5未耗尽预算时已采到LOST→ACQUIRE，仍有单侧抽动、跨中心、丢牌。最后3/5/4/3/40会话对照同样INCOMPLETE，未改RTL；已停止本轮测试，搜索停靠尚未通过。

- E10从画外发现并锁定目标、短暂进入APPROACH后仍会失锁重搜，本轮最终NOT_FOUND/SCAN_BUDGET，未完成停靠。用户确认固定目标及最后停止；反向SEARCH没有触发，有限回扫实物效果尚未验证。
- 历史search4有三次整圈观察及13.6秒记录；当前search3仅两次单圈加一次双圈参考、采用15.1秒保守预算。精确360°与固定时间自动停止角误差尚未测，实验室环氧地面未测。前两次起步单侧前冲、前移3.5/2 cm，根因未定位。蓝5/6没有单独地面任务证据（用户已取消本轮单测）；350mm精确停车误差、完整任务时间及图像变化到UART响应延迟仍未全面测量；累计命令时间不是航向反馈。
- E5真实蓝1任务未停靠，已观察对准摆动、失锁和扫描预算耗尽；E7真实第01–05轮同样未完成停靠，保留POWER窗口无ARM、线缆近距中断、单侧短促动作和跨中心等事实。E6功能仿真通过但时序FAIL，从未下载；E7独立R6、Full Compilation/post-fit及下载通过，解决时序验收问题但未证明实物控制问题解决。两秒连续直行的“基本是直的”是隔离证据；E8连续差速纠偏已通过本版聚焦检查、270.641086秒正式R6、Full Compilation/post-fit及下载读回；零速预检蓝1锁定4/4。真实蓝1首轮已取得板上DOCKED和约3.18秒未ARM/零速驻留，用户确认持续向前、无明显偏转及约335 mm终距；末段对准/重确认约25秒仍需改善，左轮多走约1 cm只是用户不确定估计。蓝2已记录红2事件/重锁/ARM，另有窗口外用户前进停车观察和事后终态，但缺连续运动日志，不补造完整闭环或精确误差。蓝3实体POWER及真实接近/减速/差速微调/停靠已有完整本轮记录与用户反馈；蓝4也完成停靠，但起步抽动/偏右、末端约17.1秒修正和最终仍略偏右保留。用户已取消本轮蓝5/6单独地面任务，不再作为待执行项；两者仍只有静态视觉覆盖、没有单独地面task证据。蓝4画外搜索已实际执行，但未持续锁定，最终SCAN_BUDGET/NOT_FOUND，自动撤权/归零；此闭环项未通过，E9有限反向回扫源码已冻结、定向回归及正式R6通过，Full Compilation/post-fit与下载身份读回也已通过，实机仍未完成画外搜索停靠：E9发现/锁定后反复对准，60秒观察窗到限由主机STOP，未到DOCK；本轮没有反向SEARCH，回扫物理效果未验证，不能用预锁定目标的停靠成功覆盖。
- 实物J3近停、滞回、恢复和停靠状态已有上述E4架空证据。E4地面首轮已记录真实invalid距离触发HOLD/零速；E5真实空旷6/6读回FAR且用户确认显示，三圈分别记录10/13/15个FAR运动快照且无HOLD。长期连续性及真实视觉闭环仍需验证；经尺子核定的250/300/350mm边界与绝对精度仍待完成，FAR不能读作实测4米，旧4000/validfalse也不能确认唯一电气原因。
- SW6颜色信息与两页自动交替、SW7空隙“无标牌”及蓝1覆盖中心的`ID:B1`已获实物确认；UNKNOWN/拒识原因的实际显示、16槽同时占满和中心歧义仍待验证。
- SW8正常/旁路三对静态视觉比较已完成；地面运动中的同场景闭环对照，以及持续移动、遮挡、不同光照仍需后续实测。地面扫描、SW6/7和其他进行中的验收以分项新记录更新，不从本次静态结果推定通过。
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
| `firmware/E7070012/PartBDebug.sof` | 当前E12发布SOF，来自成功构建且已实际下载的产物；画外搜索停靠缺陷如实保留 |
| `docs/ECHO7_Integrated_Datasheet.pdf` | 当前集成版数据表 |
| `docs/REPAIR_RESULT.md`、`VERSION_README.md`、`OWNERS.md` | 分版本结果、迭代记录及来源/成员归属 |

保留工程、RTL/TB、runner、真实相机输入/model/replay、最终SOF及报告所需测量值。编译数据库和仿真缓存不作为源码；不新增逐文件SHA清单或重复凭据包。原课程/IP声明保留；A/C成员SID待补，不虚构归属或人工签核。
