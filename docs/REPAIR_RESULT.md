# ECHO-7 本次修复与实机记录

日期：2026-11-04～11-05（Australia/Sydney）。工程：`C:/Quartus_Projects/ECHO72.0/github_publish/MTRX3700_MajorProject`，保留基于`dc1db23`以来的历史工程与用户改动。本次发布E7070012原始构建、下载身份、协议/控制/R6、真实静止pulse读写均有独立证据。五轮地面观察保留：三轮短时INCOMPLETE、一轮仅回正诊断进入APPROACH即主动STOP、第五轮60.0399573秒仍INCOMPLETE并停于近障HOLD。主线搜索停靠未通过；后续第六轮连续差速获用户确认，第七轮独立近距DOCKED，第八轮搜索发现后仍INCOMPLETE；不拼成单次主线完成。第九轮turn4有限回正获反馈、首次APPROACH即STOP；第十轮完整搜索INCOMPLETE60.0024068秒；5/5逻辑请求不证明物理直行。BCTL/CCTL使用真实BUILD_ID，须配套新版主机/Tcl。历史成功与失败不互相覆盖。

## E14 当前进度

最终E7070014源码已冻结，定向、完整构建/四角时序及实际下载/零速预检通过；最终fresh R6已PASS233.259611秒，真实SW→红2→搜索→DOCK仍待。E13时序FAIL、未下载；当前实板已确认E14。完整E14参数/初始化说明及独立结果见本文末段。

### E14 已完成的定向验证（尚非整板或实机验收）

冻结源码的定向结果 `motion_policy_20261104T220025097074Z/result.json` 为PASS、18.9839668秒：四字段策略覆盖11616种合法组合、11687项检查；debug251项；真实adapter/control基线2049项及500条完整UART；初始化启动门47项。随后 `motion_policy_20261104T220112003036Z/result.json` 的最终debug254项另覆盖生产启动值与KEY0恢复。主机工具31项、HOST_RUNNER18项通过。正式R6的17个正常场景加mutant已在最终fresh运行通过（233.259611秒），最终Quartus时序也另行通过；完整实机仍待，不以仿真替代。

## E12 与较早版本的历史结论与证据边界

截至下述E12历史轮次，发布版本为 **E7070012**；该轮只补充同SOF/同参数的实机记录，没有新RTL、编译或R6。原正式R6 **223.404755秒（13 PASS＋CAUGHT）**、Full Compilation1163.903秒＋post-fit26.783秒、下载及静止pulse读写证据保留。此前第七轮从约41 cm重新POWER的独立任务达到DOCKED，J3 292 mm与探头前端尺量约370 mm差异未定；它不能替代60 cm或画外搜索闭环。其余真实搜索失败、左右起步/过冲问题仍按轮次记录。

后续OLED确认UGV Rover/version0.9，同E12重下载并恢复实验tune3/4/5/4/30、pulse200/200/60/6及15.1秒基准。T131仅关闭底盘RAM自动反馈，独立零速RX由约11 kB/s变为五样本0新增。连续改值trial1因真实500 mm诊断边界提前结束且没有物理验收；trial2已观察5/5→5/4→5/5三段，用户确认较快→较慢→较快→停车。单次ALIGN→完整零速驻留→APPROACH隔离也取得逻辑证据，用户确认“两侧轮子都一起走的”。这些是限定试验结果，不是精确轮速、直行精度或flowoff因果修复证明。

紧接着的一轮**真实相机画外搜索仍INCOMPLETE，60.0067485秒未DOCK**，由观察窗结束后的host STOP收尾；729 C/90 B、host START/合成写入/heartbeat均0。用户看到找到蓝4后反复修正、牌先到右边再到左边、最后居中，末段两轮共同前进后停；是否又发生大幅末段纠偏不确定。用户尺量**相机到标牌垂直距离46 cm**，板上J3末读数**407 mm**，测量起点不同，不能计算为同基准误差。收尾V1未ARM、permit0、左右0、zeroSent、IR0/HOLD0且cleanup无错误。实验组合仍不是推荐设置；完整搜索停靠未通过，原因未证实。SOF复位默认未改，不新增E13初始化或重复搜索结论。

历史已发布E11为 **E7070011**，该轮收尾VISION_ONLY、未ARM、零速；默认参数与当时最终实验配置分别记录。E11加入停车调参及失锁后完整停车重确认。控制定向runtime两sign各996检查/358完整UART、旧参数847/289通过；正式R6首轮302.015209秒超时FAIL保留，优化调度后的全新第二轮 **219.199994秒、13 PASS＋CAUGHT、targetMet=true**。Full Compilation1375.853秒＋post-fit26.278秒PASS，setup/hold +0.237/+0.120 ns，实际下载E11已核对。实板停车五项参数写入/独立读回、search改变使扫描标定失效及默认恢复均PASS；初始停车调参阶段未运动；后续已有真实地面试验，首轮与search3搜索均NOT_FOUND，turn3隔离仅抽动/INCOMPLETE。该轮只调参、不改E11 RTL；最终实验3/5/4/3/40、扫描15.1秒；turn5和approach4对照均INCOMPLETE，降速未解决抽动/过冲。本轮停止追加测试，组合仅作实验记录，不能称实测轮速或停靠通过。

历史E10源码、SOF及当时实际板上读回为 **E7070010**，实测收尾VISION_ONLY、未ARM、零速。用户接受较宽的居中范围后，本版默认改为U90–150（相对120为±30），并允许350 mm以外、已经新鲜锁定且U75–165的目标在START或完整ACQUIRE确认后直接进入APPROACH，减少不必要的停车原地对准。本版定向回归已PASS：默认正/负两sign各804检查/275UART、旧严格参数817/278，共29.1663517秒。正式R6已独立PASS271.31444秒、13 PASS＋CAUGHT，达到285秒目标；Full Compilation1260.493秒及post-fit25.832秒已独立PASS，setup/hold最差+0.909/+0.118 ns，实际下载和E10身份核对通过；蓝4零速校色预检4/4锁定。实机已从画外发现并锁定蓝4，短暂APPROACH后LOST并重启搜寻，最终 **NOT_FOUND/SCAN_BUDGET**；观察任务约22.21秒，未DOCK、未触发反向SEARCH。用户确认纸板固定、最后车轮停止；画外搜索停靠尚未通过。下面保留E9和更早版本的独立证据。

**此前E8：蓝1、蓝3、蓝4已分别取得真实接近停靠及用户实物结果。** 观察ARM至DOCKED分别约29.315066、15.726722、26.139371秒，终态J3分别329、321、316mm；各保持未ARM/零速超过3秒后正常收尾。蓝1/4为主机START，蓝3为实体POWER，均为真实相机且无合成写入。用户确认实际前进和停止位置；蓝4同时明确起步抽动、偏右及最终仍略偏右，蓝1/4末端约25/17秒微调仍慢。三轮都从已见目标开始，无SEARCH，不外推画外目标搜索或全部六牌。

**E8独立验证：**两种TURN_SIGN各433检查/88完整UART PASS（6.7496263秒）；正式R6 PASS，13项PASS + CAUGHT、270.641086秒、targetMet=true；Full Compilation **1159.722秒**及post-fit **25.963秒PASS**，ALM29281/32070（91%）、setup/hold最差 **+1.021/+0.121ns**、未约束0。原始E8 SOF已实际下载并读回版本，发布副本与原产物逐字节一致。蓝2红2事件/新选择/锁定/ARM已有板上记录，但日志段全程零速；日志后用户前进观察及事后DOCKED仅构成分段佐证。蓝3已确认E8实体POWER任务。用户已取消蓝5/6独立地面测试；最后沿用蓝4的画外搜索已经执行，13.6秒累计搜索预算耗尽后NOT_FOUND，未到ALIGN/APPROACH，不能记为搜索停靠通过。

**E9当前验证边界：**仅为正向SEARCH曾观察到目标、停车确认后又失去目标的情形增加反向小步；每步最多150ms、全任务最多3步、反向也消耗同一搜索预算，每步后必须完整零速UART、1.5秒保守驻留及新fence后三帧确认。两种TURN_SIGN各**696检查/245完整UART PASS**，编译加两次仿真合计**20.8500433秒**。本版独立正式R6已PASS，274.530007秒、13 PASS + CAUGHT、cleanBuild=true、targetMet=true、退出0；Full Compilation1218.109秒＋post-fit26.779秒独立PASS，已下载并核对E9身份；本版零速校色/蓝4锁定预检4/4通过。画外蓝4搜索实机INCOMPLETE：发现/锁定后反复对准，60秒观察窗无DOCK，主机STOP收尾；本轮未触发反向SEARCH，不借用E8停靠结果声称E9回扫机械效果通过。

**历史E7070007：**正式R6独立PASS（13 PASS + 1 CAUGHT、265.276162秒），Full Compilation/post-fit PASS（1147.755秒+26.087秒），ALM29320/32070（91%），setup/hold最差+0.864/+0.117ns、未约束0，实际下载与读回成功。真实任务02遇缠线/近距HOLD；任务04/05均未DOCKED，实物出现单侧短促动作/跨中心；两秒独立合成居中直行则获实际基本走直确认。这些失败及隔离试验促成E8，不能把E7构建PASS写成地面停靠PASS；当时各次收尾VISION_ONLY/未ARM/zeroSent。

**E7070005历史构建与实机阶段：**最终R6为13 PASS + 1 CAUGHT、239.403059秒，达到285秒目标；Full Compilation与post-fit门检PASS（1173.143秒+25.799秒）。原始SOF已下载并读回E7070005，静止蓝1锁定与FAR分类实测通过；三次地面IR计时13.561176/11.075500/11.436358秒均获物理满圈确认（3/3），已实际设定13.6秒近似有界扫描参数；超转10°/5°/45°、前两次起步单边前冲及漂移保留，第三次按晚且未见前冲。精确360°及真实视觉地面闭环仍未通过。** 首次新套件303.500928秒，12项完成PASS，第13项reader编译超时，mutant未运行，不能称完整功能断言全部通过。生产顶层`TURN_SIGN=-1`、左右直行极性不变；控制回归两种显式参数各269项通过，生产负参数的固定25fps像素到UART回归12帧通过。E4地面首轮约75°顺时针后因无效测距进入HOLD，未完成一圈；左右真实静态样本随后确定旧低U转向背离车体左目标。用户又明确修改正常无回波处理需求，E5将完整长回波回低分类为FAR，同时保留近距、IR及异常信号保护。详细证据和新需求边界见文末。三圈设置时板上E7070005、VISION_ONLY/未ARM/零速、IR锁存；scanBudgetUs=13600000、scanCalibrated=true，复位/重下载后失效。后续真实任务及短转诊断的状态单列，当前IR状态不沿用三圈结束时的值。

此前 E7070004 的独立完整构建和下载记录：控制定向仿真 **254检查PASS**，完整干净副本 R6 **12 PASS + CAUGHT，219.556074秒**，满足用户285秒目标。Full Compilation **1121.141秒PASS**，post-fit门检 **25.868秒PASS**；ALM29576/32070（92%），最差setup/hold **+1.633/+0.118 ns**，未约束项0。该版新SOF于 **22:31:50 AEDT** 下载成功并读回 **E7070004**；真实红2重新选择、等新锁定、ARM/ALIGN的板上链路通过，用户确认实物启动，并最终澄清“蓝一脱离后就停车了”。末状态为VISION_ONLY、未ARM、左右逻辑零速，用户确认已经停止。主机两秒观察后STOP的独立机械停车时刻未测，不据此宣称两秒实物定时停车；002架空轮子/IR观察仍保留为该版独立记录。以上时间、资源和时序均属于004，不能标成005结果。

前版实机证据分别成立：E7070002验证过架空轮子、真实IR、合成感知经真实C/J3/UART的动作与取消；E7070003验证过真实视觉坏帧后的健康/锁定恢复。两版各自也暴露了后续需要修正的现场问题，完整失败记录保留。本文不把这些历史测试写成004已通过。

| 证据层 | 能证明什么 | 本次不据此推导的结论 |
|---|---|---|
| 离线模型 | 指定像素/场景下的算法判断、历史问题复现 | 当前RTL、板卡或车辆通过 |
| RTL_SIM | 对应源码和输入层的时序、状态、接口与断言 | 真实相机持续稳定、实物轮向或地面停靠精度 |
| Full Compilation + 四角门检 | 指定设计可装入器件且所检查约束通过 | 已下载该SOF，或车辆已完成任务 |
| 板上身份/状态/UART读回 | 实际加载设计、传感输入及控制链状态 | 车轮物理方向、车体停稳或360°转角精度 |
| 用户架空观察 | 对应测试下的实际车轮动作/停止/方向 | 六车位落地验收或扫描标定 |

完整开发顺序见 [VERSION_README](../VERSION_README.md) 的2026-11-04记录；这里保留验收事实、复现入口与限制。

## 已实现的行为

- `rtl/member_c/perception_adapter.sv`：SW0–SW5独热选择、20 ms整体稳定确认；未启动也请求真实追踪；SELECT/CLEAR握手、tag与采集边界；无目标健康帧与目标锁定资格分离。
- `rtl/member_c/member_c_control.sv`、`motion_fsm.sv`、`safety_arbiter.sv`：有界SEARCH、ACQUIRE、ALIGN、APPROACH、DOCKED、LOST、HOLD、NOT_FOUND；先零速JSON完成，再驻留和三帧新观测；取消、超时和完成均不能自行恢复旧任务。
- `rtl/member_c/memberCBoard.sv`、`chassis_command.sv`：真实IR/J3保护；POWER第一次释放IR、第二次新按压启动；真实新测距连续三次恢复；完整JSON、零速优先及零速发送完成状态。
- `rtl/top/echo7IntegratedTop.sv`、`rtl/debug/chassisDebug.sv`、`syntheticPerception.sv`：同一生产SOF三模式、完整感知接口切换、CCTL事务、合成25 Hz报告、500 ms主机会话租约。电脑无法直接写轮速或超声距离。
- `rtl/interaction/fixedSheetInteraction.sv`、`perceptionCore.sv`、`perception_pkg.sv`：红1校色；按用户追加需求，红2重新选择当前实体拨码并请求开始。红2需先移开三帧、再呈现三帧；上电已有卡不启动。模式、STOP、IR、选择和安全边界清除旧卡授权，不清校色。语音始终禁用，旧speech-arm明确拒绝。
- 红2的004启动条件：仅未启动/终态接收一次重新选择，活动任务不重置累计扫描预算。INTEGRATED未标定时等当前新tag目标三帧锁定，已标定可在健康新帧后搜索；1秒窗口内未满足则取消，晚来的目标不复活旧授权。VISION_ONLY仅重新选择，CHASSIS_INJECT忽略真实红2。
- `rtl/debug/memberBVgaDiagnostics.sv`：SW6显示全部16候选的两页诊断，每页8个、约2秒轮播，包含拒绝候选、UNKNOWN和原因；SW7保留中心局部采样。复用单HSV转换器和RAM。
- `tools/chassis_debug.py`、`tools/tcl/chassis_session.tcl`：同一持久STP会话的CCTL/BCTL读写、注入、序列播放、心跳和STOP；只读状态不改任务。
- `tools/echo7.py`、`check_repository.py`、`export_submission.py`、datasheet工具及R6 runner：支持当前集成顶层、新产物路径和必要检查；不再强制旧B逐文件SHA凭据链。

详细开关、IR、模式及可执行命令见根目录 [中英双语README](../README.md)。[ECHO7_Integrated_Datasheet.pdf](ECHO7_Integrated_Datasheet.pdf)现为两页，第一页介绍功能、组件、模式、红蓝牌及操作/显示，第二页是正式R5指标；版本来自RTL header。[ECHO7_R5_Datasheet.pdf](ECHO7_R5_Datasheet.pdf)为独立一页R5表，export的`--datasheet`应指定此文件，不能传两页Integrated。指标定义/项目目标来源见[R5_TARGETS.md](R5_TARGETS.md)及`tools/data/echo7_r5_targets.json`。E14三次实测未齐时acceptance/claimed grade保留PENDING，不用历史E4/E12拼接成绩。详细验证另存于[integrated_datasheet_metrics.json](integrated_datasheet_metrics.json)与本文，产品页不填测试计数；未完成的落地指标及独立停车时刻测量不被板上状态替代。

### 关键现场修正的先后顺序

1. **先修基础控制和接口，再构建集成顶层。** 选择、健康资格、三帧锁定、实际零速发送、IR新按压和J3新测量是前置条件；没有把主机注入做成绕过控制器的直接轮速写入。
2. **用户追加红2动作需求。** 附件旧NO_ACTION不再适用；增加重新选择、授权窗口、专用交互边界复位和旧事件时间过滤。首轮资源报告超限后只做候选诊断分页调整。
3. **E7070002先通过构建与架空动作，再暴露候选溢出永久阻断。** 用户移动裁切标牌确实改善了画面，但不能修复历史sticky位永久禁止健康的逻辑问题，因此需要003代码修正。
4. **E7070003在实板验证恢复，然后真实红2又暴露启动过早。** 请求tag确实改变，问题发生在第一健康帧与第三帧锁定之间；终态不自行重启是预期安全行为，不能通过取消这一限制掩盖早起问题。
5. **E7070004只收紧未标定红2启动资格。** 新增针对前两帧等待/第三帧启动的断言，重新通过完整R6、Full Compilation和四角门检，新SOF已下载并读回版本。真实红2实测tag3→4，在新锁定后ARM/ALIGN；不发心跳仍保持正式模式授权，短暂视觉丢失时逻辑零速重确认，最后STOP读到零速发送完成。用户先反馈不会自动停车，随后澄清蓝1脱离后已实际停车；最终VISION_ONLY/未ARM且实物已停。零速发送完成本身不等于实物停稳，用户观察独立记录。
6. **E4首次落地暴露方向与正常空旷回波处理问题，形成E7070005候选。** 先保留地面首轮无效记录，再用真实左/右目标零速观察核对U轴；随后只改有效转向参数，并按用户新指示区分正常量程外回波与故障。方向回归通过不等于新SOF已构建或已经上车，005后续验证单列。

## 验证记录

模型和仿真只表示对应输入层的结果，不算真实相机或车辆验收。

| 检查 | 已执行结果 | 用时/记录 |
|---|---|---|
| CCTL与合成源ModelSim自检 | PASS，58检查、20报告；半事务、背压稳定、连续帧、租约和复位不重放 | 编译/仿真约1.31秒；`build/repair/cctl/modelsim.log` |
| C控制链ModelSim自检，含红2 | PASS，197检查；实际解码15条UART（转向3、前进3、零速9） | 编译/仿真1.27秒；`build/control_repair/control_red2.log` |
| E7070003坏帧恢复自检 | PASS，236检查；历史溢出位保留、二次坏帧、新fence及三相邻帧恢复、RESOURCE_DROP、硬故障仍拒绝；实际UART15行 | 编译/仿真1.79秒；`build/control_repair/control_overflow_recovery.log` |
| E7070004红2启动时序自检 | PASS，254检查；未标定时前两ACQUIRING帧不启动、第三锁定才APPROACH；健康NOT_FOUND不启动、超时后的晚锁不复活 | 编译/仿真1.97秒；`build/control_repair/control_red2_uncalibrated.log` |
| 真实NEC/J3/UART管脚模型 | PASS，492检查、9次J3测量、运动3条/零速6条；50 MHz、115200和实际NEC时序 | Verilator 5.050运行97.734秒；`build/control_repair/pins_verilator.log`。二进制编译于红2加入前，新增红2另测 |
| 早期像素→B报告→真实C→UART定向记录 | PASS，固定25 fps共12帧/12报告，搜索、单帧发现停转、新fence三帧、左/中/右、丢失及STOP | ModelSim约311.81秒；`build/repair_vision/tb_pixel_uart_repair/run.log`。早于后续红2边界及分页修改，最终源以E7070004 R6为准；不能称此项为R6 300秒通过 |
| 红2与校色/JTAG兼容 | 定向自检PASS；移开/新呈现、持卡不重复、忙时抑制和事件背压 | 见`build/repair_vision/`各运行日志 |
| 分页VGA | PASS，约1538986个像素及16候选、页面冻结、中心关联、背压/三bank | 约8.95秒；`build/repair_vision/memberBVgaDiagnostics_tb/` |
| 真实历史输入模型 | frame251全部八个正式标牌识别成功；frame30321蓝6上游主色区域截断，几何拒识 | 历史输入和期望未改；不按数字或固定位置特判 |
| E7070002正式R6 | **PASS：12项及CAUGHT，满足用户285秒目标和课程300秒门槛**。Verilator 5.050、干净副本；连续帧/过载共用本次新编译二进制、独立进程并行；编译jobs=4，输入和断言不变 | **245.451876秒**，退出0，targetMet=true；`build/member_b/20261104T101906_817193Z_verilator_course/result.json` |
| E7070003正式R6 | **PASS：12项及CAUGHT，包含现场坏帧恢复修正，满足285秒要求**。相同完整干净副本入口、Verilator5.050、jobs4和两场景并行 | **221.258456秒**，退出0，targetMet=true；`build/member_b/20261104T103755_574462Z_verilator_course/result.json` |
| E7070004最终正式R6 | **PASS：12项及CAUGHT，包含红2等新目标锁定的修正，满足285秒要求**。完整干净副本、Verilator5.050、jobs4、独立场景断言全部保留 | **219.556074秒**，退出0，targetMet=true；`build/member_b/20261104T110801_416299Z_verilator_course/result.json` |
| 独立故意坏模块 | **CAUGHT**：将tracker的三帧锁定故意改成两帧，真实Verilator仿真被原断言捕获；生产RTL未改 | 6.861秒；`build/repair/tracker_mutant/result.json`。独立补测，不将上面的R6 FAIL改写为PASS |
| 主机与结构 | 68项工具定向测试PASS；结构检查48个bench、60个工程依赖PASS | 工具Agent实际运行结果；不将结构通过当作RTL或硬件通过 |
| 最终文档/提交导出 | 当时README三件精确白名单（E14现改两件）；结构测试6项PASS（1.613秒），实际48个bench/60个依赖检查PASS；已有submission测试14项PASS（0.226秒） | 当时导出包括独立英文README及指标JSON；E14改为单个双语README；OWNERS覆盖277个源文件。属于发布工具检查，不累计为新RTL或实机测试 |

R6首次串行尝试在300秒截止后清理，总计303.055秒而FAIL（9项PASS、后续未完成），记录保留在`build/member_b/20261104T100142_083131Z_verilator_course/`。并行两个独立系统场景后290.761秒全PASS，满足课程但未达到用户285秒；随后编译jobs=4得到上述245.452秒。现有同次调用hash缓存实际避免一次约16秒的重复core编译。重复文件hash测量仅0.01163秒，无需新增逐文件哈希表；没有复用上一次调用的二进制。

## 构建与硬件

首次构建在用户追加红2后停止；其子流程资源检查报告32238/32070 ALM，不能fit。随后将候选诊断从18组记录缩减为10组、两页覆盖16候选。该失败产物没有下载到板上，也不作为最终构建。

E7070002（包含红2与分页诊断）Full Compilation **PASS**，Quartus Prime Lite 18.1.0 Build 625，退出0；完整编译1203.431秒，独立post-fit时序门检29.492秒。ALM **29417/32070（92%）**，M10K **357/397**，DSP **51/87**，寄存器41220。四角最差setup **1.164 ns**、hold **0.078 ns**，未约束路径0；CDC物理约束与63条同步链覆盖检查PASS。MTBF数值验收未评估。

完整编译92条warning、0 error，没有Critical Warning；保留并检查了宽度截断、未用信号/管脚、PLL reset/补偿、相机PCLK非专用clock管脚、JTAG时钟重复声明等信息。未通过放宽时序或删除CDC约束取得通过。完整日志和四角检查见`build/member_b/20261104T100141_653795Z_build/`。

E7070002产物：`build/member_b/20261104T100141_653795Z_build/source/quartus/output_files/PartBDebug.sof`（6706156字节）。2026-11-04 21:23 AEDT通过`echo7.py program --sof <上述路径>`下载成功，板上BCTL读回设计版本E7070002匹配。下载控制台记录`build/repair/program_console.log`。当时下载的是该次新编译产物。

用户确认：底盘架空，电气连接已接好；SW0上拨、其余下拨，蓝1在相机前。已通过USB-Blaster枚举真实DE1-SoC，FPGA链位置2。初始板上没有可读BCTL/CCTL；新SOF已成功识别调试链路。主机持久STP的stdout缓冲问题已改用明确flush的文件响应通道解决，连续STATUS/BSTATUS/STATUS实测43/262/38ms，另有7项主机测试通过；见`build/repair/transport_check.json`、`host_ipc_validation.json`。

E7070002实机：

- **CHASSIS_INJECT通过**：真实SW0/J3（365–370mm）和IR参与，U=80/120/160分别得到逻辑轮速(-4,+4)、(+3,+3)、(+4,-4)cm/s；停止心跳后取消授权并完整发送零速，续心跳不自行启动。健康无目标帧允许搜索，1秒累计转动预算后NOT_FOUND、撤销授权并零速。用户明确回复“观察到了”车轮转向、同向转动和最终停止。证据`build/repair/hardware_injection.jsonl`。
- **真实IR通过**：架空运行中用户按A，FPGA读回IR锁存、未ARM、轮速0；第一次真实POWER仅解除锁存，仍未ARM；第二次真实POWER启动并许可运动，测试随后STOP并回VISION_ONLY。`build/repair/hardware_ir.jsonl`、`ir_console.log`保留全序列。这段IR/安全RTL在E7070003中未变，但测试SOF明确为E7070002。
- **真实画面纠正**：首次GRAB frame11980（CRC0x7d92）红1、蓝1贴边裁切，红色活动标签18超过15容量；离线两档阈值均重现同样溢出。用户将同张A4红1/蓝1移远，同SOF重置后，VISION_ONLY连续24个不同帧、23次锁定，始终未ARM、零速；蓝1质量255，U178/V181，121×114框，红1完成8帧校色得到阈值41/24，处理57.457ms。见`build/repair/live_capture/`与`hardware_vision_e7070002.jsonl`。
- **发现并修正后续阻断**：随后又一次单帧候选溢出，历史sticky位令C永久拒绝健康资格，INTEGRATED实测因此安全拒绝ARM，并未冒充通过；记录`hardware_integrated_initial_fault.jsonl`。E7070003已修正为当前坏帧立即撤销旧资格、建立接收时间边界、三相邻新好帧后恢复；保留B历史诊断和FIFO/双bank等硬故障。E7070003实际结果见下文。

### E7070003构建与实机

Full Compilation **PASS**，1154.491秒（19分14秒），post-fit门检24.886秒，退出0、0 error、92 warnings。ALM **29373/32070（92%）**，M10K **357/397**，DSP **51/87**，寄存器41131，memory bits2802640。全部时序角点PASS，最差setup **0.967ns**、hold **0.117ns**，未约束项0；CDC与每角63条同步链覆盖PASS，MTBF数值未评估。没有放宽约束。

E7070003当时产物：`build/member_b/20261104T104155_505074Z_build/source/quartus/output_files/PartBDebug.sof`，**6706161字节**。2026-11-04 **22:02 AEDT**实际下载成功，BCTL读回 **E7070003**，与该版源码/构建标识一致。完整记录`result.json`、`timing.json`、`build/repair/program_final_console.log`。

- **现场故障恢复通过**：`hardware_recovery.jsonl`记录frame338、历史faultFlags=3仍保留，同时sourceHealthyFresh=true、targetLockedFresh=true；同一运行中未复位、未清历史故障、未ARM。此前E7070002会被这个历史位永久阻断，本次已在实板纠正。
- **连续真实视觉通过**：该版VISION_ONLY读到23个不同帧、22次锁定，始终零速；BCTL frame855、蓝1质量255、U115/V186、122×130框、处理59.478ms。见`hardware_vision.jsonl`；E7070002的24帧记录独立保存在`hardware_vision_e7070002.jsonl`。
- **轮向人工核对**：合成居中U120时实际APPROACH，逻辑两轮+3cm/s，用户确认“两侧都向前”；A/POWER测试中两轮反向是预期转向命令。`hardware_straight.jsonl`保留8秒观察及最后零速。该轮向/IR检查使用E7070002，电机极性、安全链在最终版未变。
- **红2现场时序问题**：真实红2使请求tag5→6，证明重新读取/选择已生效；但第一健康帧早于新目标三帧锁定，控制器过早启动而进入SCAN_UNCALIBRATED/NOT_FOUND，之后锁定也不会自动复活。用户确认识别后底盘无反应。失败完整保存在`hardware_red2_e7070003_early_start.jsonl`及对应控制台。E7070004将未标定红2pending启动延后至当前新请求targetLockedFresh，保留1秒超时和所有安全取消条件。

### E7070004构建与实机：逐项确认

该版相对003只针对红2启动资格做必要修正：控制器等待新的请求tag，并在INTEGRATED未标定时要求当前新目标已锁定。适配器的三个新观测、报告时效、配置和接收边界不变；STOP、IR、实体选择变化、源模式变化、raw模式和安全条件仍可取消pending。校准后的健康无目标搜索行为不受该额外门控影响。

| 项目 | 当前结果 | 证据/说明 |
|---|---|---|
| 控制定向ModelSim | **PASS，254检查**，1.9680123秒 | `build/control_repair/control_red2_uncalibrated.log`；15条实际解码UART，0 error/0 warning |
| 完整R6 | **PASS，219.556074秒，12 PASS + CAUGHT** | `build/member_b/20261104T110801_416299Z_verilator_course/result.json`；Verilator5.050、干净副本、jobs4 |
| Fitter | **PASS，22:28:38 AEDT** | ALM29576/32070（92%），寄存器41000，M10K357/397，DSP51/87，memory bits2802640，PLL2 |
| Full Compilation与post-fit门检 | **PASS，1121.141秒 + 25.868秒** | 本版目录`build/member_b/20261104T111202_124373Z_build/`；0 error、92 warnings；最差setup +1.633 ns、hold +0.118 ns、未约束0；88项时序检查及每角63条同步链覆盖PASS，MTBF数值NOT_ASSESSED |
| 新SOF大小/下载/板上身份 | **PASS，6706154字节**；22:31:50 AEDT下载且BCTL读回E7070004 | `source/quartus/output_files/PartBDebug.sof`；`build/repair/program_e7070004_console.log` |
| 真实红2→新选择→锁定→行动 | **启动板上链路PASS，用户确认实物启动和蓝1脱离后停车** | tag3→4，frame2900锁定蓝1并ARM/ALIGN、轮速(+4,-4)、真实J3=468 mm；003早起失败日志独立保留 |
| 当前收口状态 | VISION_ONLY、未ARM、左右逻辑零速；用户确认已经停止 | 不将停止归因于mode1；主机STOP的独立机械停车时刻未验，zeroSent仅证明发送完成 |
| 发布产物位置 | 固件及最终一页数据表按004归档 | SOF `firmware/E7070004/PartBDebug.sof`；一页PDF `docs/ECHO7_Integrated_Datasheet.pdf` |

**004真实红2完整观察**：`build/repair/hardware_red2.jsonl`及`red2_console.log`记录REAL_CAMERA/INTEGRATED、实体SW0选择蓝1，oldTag3→4。frame2900新目标锁定、taskArmed=true、ALIGN、逻辑L+4/R-4 cm/s，J3=468 mm、failure=NONE；colourCalibrated=true/config1，但scanCalibrated=false，证明无需伪造地面扫描标定也可在真实新锁定后启动。历史faultFlags=3保留。

触发后2秒不发送主机心跳，13个状态采样全部taskArmed=true、leaseValid=false，符合INTEGRATED不依赖调试租约；状态分布为7次ALIGN、4次LOST、2次ACQUIRE。触发与观察合计8个运动样本，丢失/重新确认时零速，因此这不是“连续稳定转动2秒”的证明。finally STOP得到未ARM、IDLE、L0/R0、zeroSent=true，保留INTEGRATED模式。最终BCTL frame2959读回build E7070004，蓝1q255、U182/V130、101×117框、frameGood=true，处理延迟47.652 ms；事件7/id2、issuedAtUs115678441。该延迟仅是B侧采集到处理完成，不是图像到UART总延迟。

003早起故障在本次板上启动链路已纠正，用户确认004红2后实物会启动。用户最初说“不会自动停车”，随后先确认“现在已停止”，再澄清“事实上是蓝一脱离后就停车了”，因此最终记录为**真实红2启动及目标脱离后的实际停车已确认**，不再保留泛化的“自动停车故障待查”。收口时已切VISION_ONLY、未ARM、左右逻辑零速，但不能把停车归因于切模式。

主机两秒观察后的finally STOP只验证板上授权撤销和zeroSent=true，其独立机械停车时刻未测；不宣称“两秒实物定时停车”。红2启动的是正常任务，本身不是两秒计时动作。架空条件不能完成真实车体对准或停靠，短暂视觉丢失/重新获取仍是稳定性限制。未据此宣称连续落地追踪、350 mm停靠精度或六车位闭环通过。按用户要求不再扩展硬件测试。

发布生成器`tools/render_integrated_datasheet.py`默认从项目根派生路径，读取`docs/integrated_datasheet_metrics.json`，输出`docs/ECHO7_Integrated_Datasheet.pdf`。以最终澄清后的004证据生成，pypdf检查恰好1页，并经Poppler渲染及目视版面检查；旧`build/repair/`过程文件保留。

## 复现命令与日志索引

以下命令在本项目根目录执行，表示当前工具入口；历史已完成结果仍以上表对应目录为准，不把重新执行的结果覆盖到旧文件。系统须有Quartus Prime Lite18.1、ModelSim Intel FPGA Edition或Verilator5.050及相应编译器。示例使用`python`，本机实际执行的是`C:/Users/user/AppData/Local/Programs/Python/Python313/python.exe`。

控制与CCTL定向RTL自检：

```powershell
python tools/echo7.py --modelsim-bin C:/intelFPGA_lite/18.1/modelsim_ase/win32aloem test --rtl --only tb_control_repair tb_chassis_debug
```

完整当前R6（本机Windows工具链路径）：

```powershell
python tools/run_r6_windows.py --compiler-bin C:/msys64/mingw64/bin --bash "C:/Program Files/Git/bin/bash.exe" --jobs 4
```

runner会建立本次独立输出目录和干净源码副本，记录编译输入与二进制身份，并在同次新编译后让连续帧/过载两个场景并行运行。12项是`tb_pixel_uart_repair`、`tb_control_repair`、`tb_chassis_debug`、`red2Start_tb`、`perceptionCoreContinuous_tb`、`perceptionCoreOverload_tb`、`hsvColourGate_tb`、`targetTracker_tb`、`fixedSheetInteraction_tb`、`colourSampler_tb`、`markerQueryStore_tb`、`mainColourSupportReader_tb`；另执行故意坏模块检查CAUGHT。`targetMet=true`表示285秒目标满足，不能只看其中某个bench的PASS行。

完整Quartus构建及已有产物下载的工具入口：

```powershell
python tools/echo7.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 --timeout 1800 build
python tools/echo7.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 program --sof build/member_b/20261104T111202_124373Z_build/source/quartus/output_files/PartBDebug.sof
```

上面的下载命令说明本机复现入口，实际执行事实以各版“构建与实机”的时间、版本和日志为准。当前CLI核对`last_build.json`中的原始产物身份，不接受任意路径副本；从Git取得当前发布固件的读者应按README的Quartus Programmer流程加载`firmware/E7070005/PartBDebug.sof`，或在本机重新构建后使用新生成的原始路径。下载前应先确保底盘安全放置，并按README选择模式。

一页PDF可选复现（只生成文档，不访问板卡）：

```powershell
python -m pip install reportlab pypdf
python tools/render_integrated_datasheet.py
```

脚本要求输出恰好一页；发布前另用PDF渲染器逐页看版面，不能只依赖文字提取。`docs/integrated_datasheet_metrics.json`仅保存五个可读展示字段，不引入新的逐文件hash凭据包。最终PDF与Git固件仍应按设计版本核对。

| 证据目录/文件 | 用途与保留规则 |
|---|---|
| `build/control_repair/control_red2.log` → `control_overflow_recovery.log` → `control_red2_uncalibrated.log` | 197→236→254检查各自保留，后版不冒称前版已有新增覆盖 |
| `build/control_repair/pins_verilator.log` | 红2加入前真实NEC/J3/UART管脚模型492检查；ModelSim早期超时未记PASS |
| `build/member_b/20261104T100142_083131Z_verilator_course/` | 首次303.055秒R6 FAIL，保留超时及未完成事实 |
| `build/member_b/20261104T101257_441019Z_verilator_course/` | 290.761秒完整PASS，但未达用户285秒 |
| `build/member_b/20261104T101906_817193Z_verilator_course/` | E7070002完整R6 245.451876秒 |
| `build/member_b/20261104T103755_574462Z_verilator_course/` | E7070003完整R6 221.258456秒 |
| `build/member_b/20261104T110801_416299Z_verilator_course/` | E7070004完整R6 219.556074秒 |
| `build/repair/hardware_injection.jsonl`、`hardware_ir.jsonl`、`hardware_straight.jsonl` | E7070002真实C/J3/UART/IR及用户观察对应状态，不改写成003/004实测 |
| `build/repair/hardware_integrated_initial_fault.jsonl` | E7070002永久健康阻断的现场失败 |
| `build/repair/hardware_recovery.jsonl`、`hardware_vision.jsonl` | E7070003无需复位恢复和23帧/22锁定的实测 |
| `build/repair/hardware_red2_e7070003_early_start.jsonl`、`red2_e7070003_early_start_console.log` | E7070003真实红2早起失败，后续成功另存 |
| `build/repair/hardware_red2.jsonl`、`red2_console.log` | E7070004真实红2启动板上链路PASS，含13次无心跳采样、短暂LOST/ACQUIRE和STOP零速发送完成；实物启动与蓝1脱离停车由用户另行确认，日志本身不证明机械停车时刻 |

上述`build/`路径是本机原始证据位置，通常不随Git跟踪整个编译数据库或工具链。发布SOF/PDF与最终交接文件在根目录README另列；不存在于仓库的本地日志不能要求远端读者凭空复现，读者应使用相同入口重新运行得到自己的记录。

## 扫描依据和仍需地面测量的项目

当前实现是累计获准SEARCH转动命令时间的有界扫描，另有120秒任务总超时。没有已验证的本机航向回包；后续E5取得当前塑胶地面三次操作员IR终止的满圈记录，并设置13.6秒经验上限，保留超转/漂移，不称精确航向闭环。[UGV02官方文档](https://www.waveshare.com/wiki/UGV02)提供IMU/底盘反馈查询，但不能据此假定当前固件字段、单位或更新率已验证。

默认10秒只用于显式启动的CHASSIS_INJECT有界调试。正式INTEGRATED在未标定时禁止无目标360°扫描，目标已经可靠可见时仍能正常对准接近。架空轮转不能标定地面360°，零速JSON发送完成也不能证明车体物理停稳。

**本轮剩余执行范围：**用户明确“我觉得5/6都不用单独测了，1-4已经说明了性能”，因此取消蓝5/6独立落地试验，不再列作本轮待执行；只沿用蓝4补一次画外起始搜索到停靠，再整理文档/PDF/导出和发布。**蓝1/4主机START、蓝3实体POWER起始的真实接近/对准/DOCKED已各完成一次**；蓝2为红2链路记录加日志后用户前进/事后终态佐证，缺口保留，不补跑。六牌静态识别曾全覆盖，但蓝5/6没有独立地面任务证据，不能从蓝1–4外推其通过。末端微调效率/重复性、固定预算角误差、精确停车误差/图像到UART延迟、SW8地面成组对照、复杂光照/遮挡与缺失SID继续作为未覆盖范围或缺陷记录，非本轮新增扩测计划；抽动、偏右、间歇丢锁和历史蓝6碎裂不删除。

## 续测：E7070004完整六牌视觉，保持生产RTL不变

本节追加用户要求继续验收后的新证据，不重写前面的构建、R6或历史失败。用户将六张蓝牌全部置于画面内，并用绿色胶带遮住红2以避免触发；板卡保持VISION_ONLY。原始资料为`build/continuation_20261104/six_cards_initial/`和`blue1.json`，汇总为`build/continuation_20261104/vision_findings.json`。没有改动生产RTL、历史相机输入或历史期望，也没有为数字6添加特殊答案。

**同帧真实GRAB：**frame26844、CRC`0x80b8`校验通过、BCTL版本E7070004。像素和结果字绑定同一帧；配置1、红/蓝最低值57/37、orientationProfile0、正常透视路径、非raw。frameGood=true，candidateOverflow/error/overrun均false，活动标签峰值红4/蓝8，处理52.889ms。蓝1–6均accepted且质量255；蓝6完整框为`[60,188,104,229]`。红1正确接受；绿色胶带遮住的红2残余与蓝色参考条作为数字候选均以GEOMETRY拒识。蓝参考条不是编号车位，其数字拒识不代表配对校色参考无效。

**实体SW0选蓝1，12次C/B只读配对采样：**耗时4.193秒；B帧27248–27347中保留12个不同帧快照，每个蓝数字均12/12接受，红1为12/12，红2为0/12。有效拒绝框共24次，均reason1（GEOMETRY）。12次均为好帧，没有候选溢出、错误或overrun；处理延迟52.864–52.878ms，均值52.873ms；快照采集年龄53.120–89.295ms。C端蓝1为12/12 sourceHealthyFresh、12/12 targetLockedFresh，全部未ARM、逻辑轮速0，模式始终VISION_ONLY。CCTL与BCTL分别冻结，不声称每对快照来自同一帧，也不把稀疏轮询当作每个25fps原生帧的连续录像。

| 输入及证据层 | 颜色门限 | 蓝6与整帧结果 |
|---|---|---|
| 历史frame30321，原已保存的离线模型 | 红41、蓝33 | 蓝6仅有`[260,177,291,207]`部分框，GEOMETRY拒识；原记录保留 |
| 同一历史像素的一次阈值单变量离线对照 | 红41保持，仅蓝33→20；reader9/colour3不变 | 蓝6恢复完整`[257,177,291,238]`并识别digit6；八张正式标牌全部接受，好帧且无溢出，活动峰值红4/蓝5；模型用时1.448秒 |
| 本次完整六牌真实相机 | 红57、蓝37 | 蓝6在同帧GRAB及12个不同帧快照中全部接受，六张蓝牌各12/12；不需要降低当前门限或改识别RTL |

该单变量对照说明旧蓝6碎裂与颜色阈值、光照条件相关，不能归结为数字6分类器必须特判修复。离线降低门限不是板上改阈值的证据；当前实图在更高蓝门限37下仍成功，也不能保证其他光照都稳定。现有结果支持优先纠正完整入镜、均匀照明及有代表性的校色条件，并保留未知/遮挡候选拒识。它不构成对所有历史场景的永久修复承诺。

本次GRAB有9个有效候选，第二页可显示索引#8的蓝2，第一页包含有效蓝牌、红1与拒识候选。候选数据存在不等同于VGA目视验收；已取得的部分SW6/7用户观察单独记录在本节末尾。下段追加已取得的实体拨码结果，SW8正常/旁路三次公平对照仍待对应记录。本节不声称六车位落地闭环或360°扫描已完成。

### 实体SW0–SW5、全零与冲突选择：441次完整配对

`build/continuation_20261104/six_switches.json`实际运行150.054秒，441次完整CCTL/BCTL配对全部保留，B端441个不同帧、C端405个不同缓存帧。分析文件为同目录`six_switches_analysis.json`。全程E7070004、VISION_ONLY、配置1、红57/蓝37、正常透视模式；**441次均未ARM、motionPermit=false、逻辑L/R=0**。六个one-hot均出现目标身份正确且C/B锁定的实际样本；全零17次、冲突27次，其中mask3的稳定冲突连续26次，并非只靠一个拨动瞬间证明冲突处理。

下表按CCTL实际`stableMask`的16个连续区间划分，样本索引从0开始。C健康/锁定、B锁定及坏帧均为次数，分母为N；B的NONE表示markerType=NONE、digit15、targetSelected=0。没有因坏帧、过渡或未锁定而删样本。

| 样本索引 | stableMask / 选择 | requestTag | N | C健康 / 锁定 | B报告身份 | B锁定 | B坏帧 |
|---|---|---|---|---|---|---|---|
| 0–199 | 1 / 蓝1 VALID | 11 | 200 | 200 / 197 | 蓝1×200 | 197 | 0 |
| 200–203 | 0 / NO_SELECTION | 12 | 4 | 0 / 0 | NONE×4 | 0 | 0 |
| 204–226 | 2 / 蓝2 VALID | 13 | 23 | 23 / 22 | 蓝2×23 | 22 | 0 |
| 227 | 6 / CONFLICT过渡 | 14 | 1 | 0 / 0 | NONE×1 | 0 | 1 |
| 228–229 | 0 / NO_SELECTION | 15 | 2 | 0 / 0 | NONE×2 | 0 | 1 |
| 230–257 | 4 / 蓝3 VALID | 16 | 28 | 27 / 24 | 蓝3×28 | 24 | 0 |
| 258–260 | 0 / NO_SELECTION | 17 | 3 | 0 / 0 | NONE×3 | 0 | 1 |
| 261–282 | 8 / 蓝4 VALID | 18 | 22 | 19 / 16 | 蓝4×22 | 15 | 2 |
| 283–284 | 0 / NO_SELECTION | 19 | 2 | 0 / 0 | NONE×2 | 0 | 0 |
| 285–313 | 16 / 蓝5 VALID | 20 | 29 | 28 / 23 | 蓝5×29 | 23 | 0 |
| 314–315 | 0 / NO_SELECTION | 21 | 2 | 0 / 0 | NONE×2 | 0 | 0 |
| 316–345 | 32 / 蓝6 VALID | 22 | 30 | 30 / 26 | 蓝6×30 | 26 | 0 |
| 346–349 | 0 / NO_SELECTION | 23 | 4 | 0 / 0 | NONE×4 | 0 | 0 |
| 350 | 2 / 蓝2短过渡 | 24 | 1 | 0 / 0 | 蓝2×1，ACQUIRING | 0 | 0 |
| 351–376 | 3 / 稳定CONFLICT | 25 | 26 | 0 / 0 | NONE×26 | 0 | 1 |
| 377–440 | 1 / 返回蓝1 VALID | 26 | 64 | 63 / 62 | 旧tag25 NONE×1，当前蓝1×63 | 62 | 1 |

原始开关与稳定值尚未一致的样本为227、281、282，`selectionMatches=false`且C健康/锁定均撤销。稳定冲突mask3的26次以及所有NO_SELECTION均没有C健康/锁定，也没有B目标选择有效。返回蓝1时样本377仍能看到旧tag25 CLEAR报告，而C已请求tag26；C保持未健康/未锁定。下一配对进入当前蓝1身份，随后恢复锁定。这是保留下来的请求边界过渡，不是把旧目标当作新目标接受。

“稳定窗”另按`selectionMatches=true`且原始mask等于stableMask统计；在首次C锁定之后继续保留全部后续失败。六个主要档位的该窗C锁定次数分别为蓝1 **197/200**、蓝2 **22/23**、蓝3 **24/26**、蓝4 **16/17**、蓝5 **23/26**、蓝6 **26/28**；冲突后最后返回蓝1为 **62/62**。因此六档覆盖成立，但不能把本轮写成441次无丢锁或六档全时稳定。首次观察到相应稳定档位至首次C锁定的轮询间隔：蓝3为0.611秒、蓝4为0.984秒、蓝5为0.993秒、蓝6为0.578秒，冲突后蓝1为0.615秒；最初蓝1和主要蓝2区间的首样本已锁定。这些是稀疏读数之间的间隔，不是实测拨动瞬间到锁定的机械/原生帧延迟。

7个坏B帧完整保留：样本227/frame30630、228/frame30639、259/frame30895、261/frame30910、279/frame31057、375/frame31863、378/frame31887。它们均为candidateOverflow和REPORT_FRAME_BAD，无candidateError/overrun。227、228、259、261、378的蓝活动峰值达到15；279与375的红峰值达到15。峰值是已观察到的资源压力，缺少这些坏帧的同期像素，不据此断言某块背景是唯一原因。每个坏样本之后均观察到好B帧，相邻读数间隔0.306–0.699秒；蓝4样本261后0.984秒在同一选择下重新观察到C/B均锁定，返回蓝1的378后0.313秒也观察到C/B均锁定。279之后在该档未记录到重新双锁便发生拨码变化，不能补写为已经恢复。

全部B报告原因为OK369、NOT_FOUND20、NO_SELECTION40、FRAME_BAD7、ACQUIRING3、REQUEST_CHANGED2；C端总健康390/441、总锁定370/441。C先读、B后读，因此样本279等可能出现C尚为锁定、稍后B已发布新坏帧，不能误当成“C接受该坏帧仍运动”；这些采样仍全部零速。无选择时C缓存frameId/年龄可能停留在旧值，B帧仍前进，不代表相机停止。本次结论限于实体六档及非法选择的真实零运动视觉覆盖，未替代地面任务验收。

### SW6/7实物目视反馈：已确认项与未确认项

本阶段用户明确回答SW6能看到候选的颜色信息。当时该反馈仅确认候选颜色诊断在实物屏幕上可见，用户尚未理解/确认翻页，因此当时两页自动切换未获实物确认；UNKNOWN、拒识原因以及所有16槽的实际显示也没有得到明确确认，不能从“候选颜色可见”推断这些项目已通过。此前分页/拒识的RTL测试结果继续保留为仿真证据。**后续已完成两页自动切换的明确实物确认，见本文末尾新增记录；UNKNOWN/拒识与满16槽仍未确认。**

本阶段用户明确确认SW7：中心落在白色空隙时能看到采样颜色，并显示“无标牌”。这项实际空白中心场景已确认，与同帧图中的中心空隙一致；它是局部采样和覆盖身份提示，不是中心独立OCR，也不扩大为已经验证中心覆盖所有数字或歧义场景。此次只追加用户目视结果，没有新的JTAG、RTL或运动试验。**后续已另行确认蓝1覆盖中心时显示ID:B1，见本文末尾；全部数字与歧义覆盖仍未扩大验收。**

### 真实J3只读响应：零速检查与距离标称值的边界

`build/continuation_20261104/sonar_response_summary.json`汇总约90秒、532个CCTL快照，全部VISION_ONLY/IDLE、未ARM、motionPermit=false、逻辑轮速0、zeroSent=true；这不是532次独立超声测量。读回距离215–528mm且全部distanceValid=true，sonarHold共25次。20个≤250mm快照全部sonarHold=true，FSM仍为IDLE；250–300mm区间7次中，接近危险边界前2次sonarHold=false，触发后5次保持sonarHold=true，与guard迟滞方向一致。因为任务从未授权，这项只证明真实距离输入和guard响应，不证明运动FSM进入HOLD或打断正在运动的车轮，也没有覆盖无回波。

用户按标称55cm初次摆放时曾长期读到379mm；按近/远重新调整后，`sonar_after_near_far.json`的12个只读快照为520/521mm、distanceValid=true、HOLD解除且仍未ARM/零速。两个记录之间没有连续观测，不能由此计算恢复时间或声称精确尺子标定。没有因379mm这个初次读数擅改距离换算系数；反射面角度、实际摆位和读回值须分别记录。

### 真实J3停靠链路：CHASSIS_INJECT架空实机及用户确认

原始日志`build/continuation_20261104/dock_hardware_01.jsonl`及分析`dock_analysis.json`：78.932秒、434个状态快照、一次明确START、清理无错误。输入层为**合成居中视觉 + 真实J3/IR/UART + 架空底盘**，不是实际相机引导的落地停靠。授权后到清理前，383次快照均为有效租约、健康锁定目标和有效距离，没有IR/fatal/HOLD；运动指令与停靠状态如下。

| 实际阶段 | 真实J3读数与板上行为 | 验证边界 |
|---|---|---|
| 远距前进 | 520/521mm，APPROACH、逻辑L/R=+5/+5cm/s | 速度是控制器指令值，未作实际轮速计量 |
| 近距减速 | 首次读到446mm时变为+3/+3，454mm时满足确认条件 | 对应350–500mm慢速区，不把用户标称45cm当精确传感器校准 |
| 正常停靠 | 首个DOCKED快照347mm，确认快照321mm；未ARM、L/R=0、permit=false、zeroSent=true且sonarHold=false | 区分正常350mm停靠与≤250mm危险HOLD；不是按尺测得的地面停车误差 |
| 反射板退远后保持停止 | 用户标称退到65cm；实际读数重新>530mm的连续12个快照跨2.194秒，末值615mm，始终DOCKED/未ARM/零速 | 未再次START，远距恢复没有自行重启 |

首次DOCKED后到清理前共83个快照、14.853秒，全部保持DOCKED/零速/未ARM。用户明确回复“对”，确认**车轮转动→减速→停车→反射板退到标称65cm仍保持停车**。这部分具有板上记录和实物观察双重依据，作为本次架空、真实J3停靠控制链路PASS。结束清理切回VISION_ONLY、IDLE、未ARM、逻辑零速、zeroSent=true。该结果仍不证明六车位真实视觉落地闭环、精确尺子标定、机械停车瞬间或落地停车误差。

### HOLD保护与恢复：保留各次结果，不提前合并为实物通过

- **HOLD01：**`hold_hardware_01.jsonl`、`hold_analysis_01.json`为66.181秒、362个状态快照，板上检查PASS，记录了危险HOLD、零速以及随后解除/重新确认后的转动命令；用户未确认这一轮实物全过程，并要求重测。因此只保留板上通过，实物恢复不标通过。
- **HOLD02：**原始`hold_hardware_02.jsonl`和`hold_console_02.log`保留。用户对第④步明确表示未看到恢复。日志显示真实距离313mm时处于ACQUIRE，主机脚本已抢先STOP；脚本要求的250<d<300mm迟滞观察窗口未连续达到1秒，不能将脚本结束或先前阶段结果解释为恢复成功。已定位并修正验收脚本；生产恢复规则仍是连续三个新的有效测距样本均≥300mm，不是“恢复需要1秒”。这条记录也不能单独推出生产RTL有故障。
- **HOLD03及独立STOP：**纠正后的新实测与用户观察已完成，结果单独列在下节，不覆盖01/02，不用dock实物通过代替危险HOLD恢复或独立STOP验收。复测保持生产RTL与距离换算系数不变。

### HOLD03纠正后实测：危险停止、迟滞、恢复与独立STOP通过

以下为纠正后的新结果；01未获实物确认、02被主机提前STOP打断的历史记录继续保留。修正的是验收脚本的阶段确认/持续观察条件，未修改生产RTL或超声换算系数。02中真实距离已进入恢复范围，但脚本仍在等待250<d<300mm迟滞观察满1秒，因而于313mm的ACQUIRE抢先STOP，用户未看到恢复；该失败不被03成功覆盖，也不是已经证实的RTL恢复故障。

`build/continuation_20261104/hold_hardware_03.jsonl`及`hold_analysis_03.json`记录86.677721秒、469个CCTL快照，六项脚本条件全部PASS、`notVerified=[]`、清理无错误。这里的空列表只表示本脚本六项均完成，不表示整个项目已无待测项。输入层仍是**CHASSIS_INJECT合成视觉、真实J3/IR/UART、底盘架空**；快照数不是独立测距次数。

| HOLD03阶段 | 实际读数与持续观察 | 板上结果 |
|---|---|---|
| 危险接近 | 真实231–242mm，5个快照跨0.647892秒 | HOLD、任务ARM保留、L/R=0、zeroSent=true，运动许可撤销 |
| 迟滞区保持 | 真实254–292mm，7个快照跨1.163541秒 | 仍HOLD、ARM保留、零速；没有仅因回到250mm以上就过早恢复 |
| 退远后恢复 | 真实367–407mm，19个快照跨3.119478秒 | 经过安全/重新确认后ALIGN，逻辑L/R=−4/+4cm/s，恢复窗口持续观察完成 |
| 独立显式STOP | 恢复窗口结束后，主机在80.491761秒发送TX4；ACK至最后状态6.093588秒 | 后续34个不同frame快照全部未ARM、逻辑零速、zeroSent=true，之后才切VISION_ONLY |

独立STOP后的采样首末跨度5.919557秒，原生frameId推进147；真实距离367–376mm且持续有效，合成源/目标锁定/租约均有效，没有sonarHold、IR或fatal，mode/selection/requestTag/configVersion保持不变。也就是说，零速不是通过丢目标、断心跳、制造危险测距或提前切模式得到；随后单独完成安全清理。34是状态快照数，不能写成34次独立超声测量，也没有测出精确机械停车延迟。

用户明确确认四个实物现象：**近处停止、迟滞区仍停止、退远恢复、随后自动停止**；本轮没有观察轮转方向，所以−4/+4只作为板上逻辑命令记录，不追加“用户确认本轮方向正确”。结合固定条件下独立TX4后的持续零速记录，本轮危险HOLD/迟滞/恢复及独立STOP功能通过，最终清理回VISION_ONLY、未ARM、逻辑零速。此前E7070004红2那一轮用户观察的是蓝1离开后停车，主机2秒STOP与其机械停车时刻未独立隔离；本次新的STOP通过**不追溯消除那个历史测量边界**。

### 续测后的当前覆盖与剩余项目

本段是续测完成后的当前清单，更新前文较早阶段的J3/停靠/恢复与STOP覆盖状态；原始失败、部分覆盖和记录范围仍保留。

- **已增加实物覆盖：**六个实体独热档位及NO_SELECTION/CONFLICT的零运动视觉验证；本阶段完整六牌各12/12接受；SW6候选颜色可见、后续PAGE:1/2自动切换，以及SW7白色中心“无标牌”、后续蓝1覆盖中心ID:B1；真实J3架空前进/减速/正常DOCKED、退远不重启；HOLD03危险停止、迟滞保持、退远恢复及独立STOP，均按各自输入层和用户观察范围记录。断电后新增静态SW8三对结果与一次旁路蓝2拒识见末节，不把前一阶段全接受结果套用到后续全部样本。
- **真实测距失效的覆盖边界：**E4的ground_scan_01已观察到实际distanceValid=false、raw4000状态使运动SEARCH进入HOLD/零速；详见末节。用户之后确认停止朝向为空旷场景，并另行修改正常无回波需求；E5候选改为完成长回波后发布FAR，不能追溯改写E4的invalid记录。E5正常FAR/异常回波的实机分界仍待验证。危险/迟滞/停靠功能通过，也不等于完成精确尺子标定或机械停车误差测量。
- **显示与旁路当前待项：**SW6的UNKNOWN/拒识原因及满16个候选槽仍未获明确实物确认；SW7中心覆盖其他数字、多个有效框的歧义场景未确认。两页自动切换和中心蓝1身份已由后续用户观察确认；SW8静态三对已完成，地面正常/旁路各三次完整闭环仍未完成，详见末节的证据范围。
- **地面与长期性能仍有待项：**固定13.6秒预算的自动停车角误差、起步不对称/漂移稳定性，六车位真实视觉落地搜索/对准/接近/停靠闭环，任务时间、图像变化到UART延迟、实际停车误差，以及持续移动/遮挡/光照变化。当前坏帧仍可能发生，441次选择记录中的7个候选溢出和间歇丢锁未被删除；新好帧后的恢复不等于图像永不失败。
- **归属信息：**A/C成员SID仍待本人补齐，不虚构成员身份或人工签核。上述架空/静态新增硬件结果没有要求重新编译生产RTL，也没有改写已取得的E7070004 R6/Full Compilation数据；后续落地证据导致的E5源码修正及本版下载另列。

## 断电后续测：2026-11-04晚至11-05（Australia/Sydney）

本节使用`build/remaining_20261104/`的新记录。用户明确设备刚断电并授权重新下载；此前配置1、红57/蓝37的截图和六档记录只作为历史证据，不作为重新上电后的当前状态。用户随后确认本次相机到标牌的物理距离为**42cm**，底盘已落地且周围清空。重新下载后的视觉/SW8记录都是VISION_ONLY零速观察，不能因为摆在地面上就声称地面搜索或停靠通过；后续真实地面首轮失败另列在本节末尾。

### E7070004重新下载与摆位纠正

`reprogram_e7070004.log`记录同一已验证E7070004程序重新下载成功，`programmerSucceeded=true`、`buildIdVerified=true`、退出码0；完成时间为2026-11-04 23:48:54 AEDT，程序记录目录为`build/member_b/20261104T124845_569847Z_program/`。没有新改生产RTL或重新声称一轮Full Compilation。下载后的`vision_after_reprogram.log`读回VISION_ONLY、IDLE、未ARM、motionPermit=false、L/R=0、zeroSent=true，配置0、未校色、未扫描标定，先保持零速检查真实视野。

`after_reprogram_scene/frame.png`及`results.json`是这次下载后的同帧GRAB：E7070004、frame863、CRC **0x8632**、320×240 RGB565、98个结果word，像素与识别帧绑定校验通过。实际图像主要为墙面/地面，右上方标牌纸条很小；这一帧红/蓝有效候选均为0，蓝1报告为NOT_FOUND、observed/locked=false、框尺寸0×0。解码数组中的16个空槽不是16个真实拒识。当前帧good/fresh，处理时间38.819ms，无当前candidateOverflow/Error/Overrun或transportFaultSticky；`faultFlags=3`与`bufferDropCount=2`是另外保留的历史状态，不据此把当前好帧改判为坏帧。

重新下载后的实际参数为配置0、`calibrated=false`、校色累计0帧、红最低值48/蓝20、orientationProfile0、reader9/colour3，SW8正常、SW9关闭。没有沿用断电前的校色结果，也没有为这张过小的图修改阈值。当前数字读取器要求候选两边至少24个native像素；先纠正距离/摆位，避免用完全无有效目标的场景做无意义的旁路比较。

用户调整后，`position_check_01.json`保留3.728392秒内6个完整CCTL/BCTL配对，C和B各6个不同帧；六种蓝牌**每种6/6接受、quality255**，每帧有效候选均为红0/蓝6。C端蓝1六次均健康、observed/locked，全部IDLE、未ARM、无运动许可、左右0、zeroSent=true；B端六次均为当前好帧，无陈旧或候选故障。配置仍为0、未校色、红48/蓝20，说明本次识别恢复来自实际摆位纠正，没有依赖更改阈值或生产算法。

| 蓝牌 | 调整后native框宽×高（像素） | 接受次数 |
|---|---|---|
| 1 | 57×51 | 6/6 |
| 2 | 57×52 | 6/6 |
| 3 | 54×50 | 6/6 |
| 4 | 54×51 | 6/6 |
| 5 | 53×49 | 6/6 |
| 6 | 52–53×49–50 | 6/6 |

B端帧号8230–8312，FPGA采集至处理完成53.174–53.199ms。J3该窗口读数为355mm，和用户从相机量出的42cm是不同测量基准，分别记录，未据此调整超声换算系数。CCTL与BCTL各自冻结、先后读取，配对不意味着同帧，也没有观测全部25fps原生帧。

### SW8正常/旁路三对：静态零速对照完成，保留超时与拒识

首个只读会话的`sw8_pairs/run_result.json`保持 **PARTIAL / exitCode2**：已完成normal1、bypass1，随后等待用户将SW8切回normal2时超过阶段/总时限，结束于229.014756秒；阶段上限180秒。`sw8_pairs_console.log`和`wait_journal.jsonl`保留该等待过程，不能删掉超时后把首个会话写为全流程通过，也不能把等待实体开关超时解释为识别算法失败。脚本只执行STATUS/BSTATUS，不SELECT、不ARM、不续运动租约。

首对文件为`sw8_pairs/normal1.json`和`bypass1.json`。续采使用独立目录`sw8_pairs_resume1/`，完成normal2、bypass2、normal3、bypass3四份，未覆盖首个PARTIAL记录；续采`run_result.json`为COLLECTION_COMPLETE、exitCode0，耗时80.414576秒，明确保留原会话来源与超时原因。两次调用各自使用一个持续JTAG会话，不能把跨会话续采写成从未中断的同一会话。

最后一次向用户提出“只将SW8上拨，其他不变，并确认三组期间相机、纸张位置、光照未变”，用户回复原词 **“done”**。`sw8_comparison_confirmed.json`记录该问题意图与原回答，校验结果为 **COMPARISON_VALID / exitCode0**；不把这个回答扩大为额外确认焦距、畸变角度或地面任务。六份原始文件及补充统计`sw8_analysis.json`保留每次样本与失败。这里的VALID表示这组静态观察满足所检查的可比条件，不表示每块标牌零失败或地面任务验收通过。

六份均为VISION_ONLY/REAL_CAMERA、实体SW0蓝1、requestTag3、E7070004、相同颜色/算法profile；每份12次完整CCTL/BCTL配对、间隔参数0.1秒，C和B各12个独立帧，held=0。SW8按正常/旁路交替，配置依次0–5，各文件内部配置稳定，均未校色；红48/蓝20、orientation0、reader9/colour3、白阈值84、anchor阈值96保持一致。全部轮询和独立帧的计数相同；总采样时长不完全相同，等样本数和间隔参数不等于精确等时采样。

| 轮次 / SW8 | 配置 | 样本 / C独立帧 / B独立帧 | 采样耗时（秒） | FPGA采集至完成最小–最大（ms） | 均值（ms） | 蓝2接受 | 其余蓝1/3/4/5/6接受 |
|---|---|---|---|---|---|---|---|
| normal1 / 0 | 0 | 12 / 12 / 12 | 6.771126 | 53.239–53.289 | 53.262000 | 12/12 | 每种12/12 |
| bypass1 / 1 | 1 | 12 / 12 / 12 | 6.143405 | 42.577–42.589 | 42.582250 | 12/12 | 每种12/12 |
| normal2 / 0 | 2 | 12 / 12 / 12 | 7.554062 | 53.236–53.268 | 53.253583 | 12/12 | 每种12/12 |
| bypass2 / 1 | 3 | 12 / 12 / 12 | 6.212045 | 42.565–42.597 | 42.586583 | **11/12** | 每种12/12 |
| normal3 / 0 | 4 | 12 / 12 / 12 | 6.003305 | 53.116–53.300 | 53.206417 | 12/12 | 每种12/12 |
| bypass3 / 1 | 5 | 12 / 12 / 12 | 6.665007 | 42.563–42.573 | 42.567750 | 12/12 | 每种12/12 |

72次C快照全部健康、observed、锁定当前蓝1，IDLE、failure=NONE、未ARM、motionPermit=false、L/R=0、zeroSent=true；72个B快照全部good/fresh、当前蓝1报告锁定，无candidateOverflow/Error/Overrun或transportFaultSticky。真实J3均为352–353mm，历史faultFlags3、bufferDropCount2保持不变。当前目标蓝1全锁不等于所有非目标蓝牌每次均接受：正常模式蓝1–6每种36/36，旁路蓝2 **35/36**、其余每种36/36。

保留的拒识为`sw8_pairs_resume1/bypass2.json`样本0、frame20748：原蓝2位置的candidate#5框为native(125,128)–(182,179)，58×52像素，accepted=false、digit15、quality0、reason3（uncertain）、segments82；这是好帧中的数字拒识，不是整帧资源故障。下一个实际采样frame20763，同一候选框恢复蓝2、quality255、segments91。没有删除这次失败，也不把单个静态拒识推断为已查明的永久算法故障；该帧缺少同步GRAB像素，不能进一步确定光照/字形采样原因。显示UNKNOWN与拒识原因的源码功能，仍不能单靠BCTL数据代替用户目视确认。

按各模式36个独立B帧汇总，正常采集至完成为53.116–53.300ms、平均 **53.240667ms**，旁路42.563–42.597ms、平均 **42.578861ms**；平均差10.661806ms。该值只描述FPGA内部采集至处理完成，**不是图像变化到UART、车辆任务用时或机械响应延迟**。两种模式各自使用其当前真实帧的数字像素，两个模式的采样不是同一帧；SW8旁路改变几何提取/透视恢复及相关anchor路径，不人为指定数字或制造失败。本场景的接受数差异不能推广为普遍准确率提升，也未测试改变透视角后的鲁棒性。

本次新增覆盖为**三对实际实体SW8切换、条件经用户确认的静态零速对照**，更新前文“静态三对未完成”的阶段状态；不是原prompt中地面正常/旁路各三次搜索—停靠闭环、任务耗时/停车误差对照，地面对照待办保留。这些SW8窗口没有落地运动。当前场景主要只有6个候选，SW6第二页空白本身不构成显示失败；随后取得的翻页与中心蓝1身份用户目视证据单列如下，UNKNOWN/拒识显示和满16槽不据此通过。

### 后续VGA实物确认：两页自动切换与中心蓝1身份

用户按说明先将SW8下拨、SW6上拨，观察约5秒，并明确确认看到了与所述一致的**PAGE:1和PAGE:2自动交替**。当前只有六个候选，因此第二页没有候选面板是正常现象；这一观察验证自动翻页，没有验证第二页装满候选或全部16槽同时有内容。SW6观察完成后已下拨。

随后用户将SW7上拨，把已识别蓝1的完整边界框移到覆盖中心小框的位置，明确确认屏幕显示 **ID:B1**，现象与提问描述一致。这是中心覆盖身份关联的实际蓝1案例；结合此前白色空隙显示“无标牌”，已分别覆盖无标牌与单一有效蓝1标牌两种场景。设计按native(159,120)与候选框关联身份，RGB/HSV仍是局部颜色采样，不能把这次观察写成中心独立OCR、所有数字通过或重叠歧义通过。

用户已下拨SW7，最后仅SW0上拨。本次证据来自用户明确目视反馈，没有新增截图或独立同帧像素绑定，也没有修改RTL。**当前显示待项只保留UNKNOWN/拒识原因、满16候选槽，以及中心其他身份/多框歧义的实物覆盖。**截至该次VGA观察，地面第一圈还处于朝向标记、地面材质及准备状态确认阶段；随后首轮结果另列于下节，现有静态/VGA通过不作为地面运动结果。

VGA观察时移动纸张后的最新只读预检`ground_preflight_status_01.json`另行读回：配置已为 **7、colourCalibrated=true**；仍是VISION_ONLY/IDLE、实体蓝1健康且锁定、未ARM、无运动许可、L/R=0、zeroSent=true，没有IR、sonarHold或fatal，真实J3为386mm且有效。扫描标定仍为false，预算仍为默认10,000,000us。该条只有CCTL，未读取当时BCTL颜色profile，因此不猜测新门限或把配置变化归因于未经记录的具体卡牌事件。此前SW8六份记录中的配置0–5、未校色及红48/蓝20仅描述各自采样窗口，不能写成此刻仍持续有效；这些历史测得值不回改。

### 地面扫描首轮ground_scan_01：真实无效测距保护，中断记录保留

`build/remaining_20261104/ground_scan_01.jsonl`及`ground_scan_01_console.log`记录首次实际落地扫描尝试，结果 **TRIAL_INVALID**，总时长21.518290秒、78个状态快照，清理错误为空。输入范围为**地面底盘、合成健康NOT_FOUND感知、真实J3/IR/UART**，不是相机搜索蓝牌或停靠闭环。主机为这一圈测量临时设置60,000,000us扫描预算，`scanCalibrated=false`，没有把默认预算或临时预算标记为已经完成机械整圈标定。

**地面材质更正：**日志首行按用户前一次口述保留了“Epoxy resin floor”。用户随后明确更正：当前是**塑胶地板**，实验室才是环氧树脂地面。原始日志不重写，但本轮在报告中按最新更正归属塑胶地板，不能作为环氧树脂地面数据，也不能将未来不同地面的时间合并成同地面三次标定。

78个快照中，65个IDLE、12个SEARCH、1个HOLD；仅12个SEARCH快照有运动命令，均为逻辑L/R=−4/+4cm/s。首次运动快照约在脚本18.508秒，最后SEARCH约21.212秒；运动快照中的真实有效J3读数范围434–1702mm。随后21.457927秒的快照已是 **distanceMm=4000、distanceValid=false、sonarHold=true、HOLD、motionPermit=false、L/R=0、zeroSent=true**，任务ARM仍保留、IR未触发，FPGA累计SEARCH命令时间为 **2,899,142us**。

这一HOLD/零速快照发生在主机清理STOP之前：随后才于21.458064秒请求TX4，收到ACK后切VISION_ONLY；最后21.518212秒快照为VISION_ONLY/IDLE、未ARM、零速、zeroSent=true，距离仍无效。因而本轮具有真实无效测距输入打断正在运动SEARCH的板上证据，而不是仅靠主机结束脚本才得到零速。用户反馈车身约转过75°后自行停下；该角度是用户近似观察，不是测得的精确yaw或误差。最初“逆时、顺时”的口述有自我更正，随后按明确俯视参考再次询问，用户确认**顺时针**；`ground_operator_notes.json`保留原话及澄清。故本轮可记录“逻辑−4/+4对应实际俯视顺时针”，但不能由此单独断定左右电机接线或固件通道名称。

4000与valid=false表明控制器收到无效距离状态，**不能仅凭该数值认定唯一原因是无回波、超声接线、物体角度或其他某一种电气故障**。本轮没有完成360°、没有IR整圈终点记录，也没有写入scanCalibrated；2.899142秒不作为一圈时间，不按75°比例外推整圈，不把保护中断前后拼成一圈。当前结论为地面首轮扫描测量失败且安全中断已记录；同一地面三次完整标定、地面视觉闭环和SW8地面对照仍待完成。

## E7070005候选：真实左右关系确定、有效转向校正及FAR新规则

### 先补真实坐标证据，再修改转向参数

用户固定车体，将同一蓝1放到车体前左、再移到前右，并明确VGA左半的蓝1位于车体实际左侧。两次只读文件均为E7070004、配置7、正常透视、orientation0、红24/蓝20，C/B各自冻结，全部VISION_ONLY/IDLE、未ARM、左右0、zeroSent=true。没有在此过程中启动电机或修改图像坐标。

| 真实位置/文件（均在`build/remaining_20261104/`） | 完整配对及健康锁定 | B报告U / V | J3实际有效读数 | 采集用时 |
|---|---|---|---|---|
| 车体前左，`body_left_01.json` | 6/6 C健康锁定、6/6 B锁定，C/B各6不同帧 | U80；V158–159 | 442–450mm | 3.426745秒 |
| 车体前右，`body_right_01.json` | 6/6 C健康锁定、6/6 B锁定，C/B各6不同帧 | U174；V157 | 436–440mm | 2.810337秒 |

这组真实位移使U从80增加至174，V基本不变，确认当前安装下U增加对应车体右侧。B的公开坐标本来就是`U=(nativeYmin+nativeYmax)/2`、`V=(638-nativeXmin-nativeXmax)/2`；C的`perception_adapter`原样传递/缓存centreU，没有再镜像或交换轴。`orientationProfile`是数字anchor方向提示，不改变这组公共坐标。无需通过改U、交换U/V或修改合成模板来掩盖转向问题。

结合首轮真实低U对应命令−4/+4且车体俯视顺时针，足以确定旧ALIGN会背离实际左目标。**这证明有效视觉转向反向，不证明具体接线错误。** 源码中L/R没有互换，但实际底盘通道如何对应实体两侧未独立追线；以前+3/+3双侧前进的观察不能排除左右互换，因为相等命令交换后不变。本次不为归因增加单轮试验。

E5仅把生产`echo7IntegratedTop`默认`TURN_SIGN`由+1改为−1，沿既有参数链进入控制器。低U及SEARCH改为逻辑(+4,−4)，高U改为(−4,+4)；原左右直行极性均−1保持。按现有UART编码，低U/SEARCH完整报文为`{"T":1,"L":-0.04,"R":0.04}`，高U相反；居中粗/细接近仍是逻辑+5/+5、+3/+3，对应UART−0.05/−0.05、−0.03/−0.03。此处JSON是源码/仿真对应关系，E5实物转向还需新SOF下载后确认。TURN_SIGN不是运行时CLI寄存器，必须随新构建生效；一圈标定须使用最终转向版本，不能沿用E4的部分转角。

### 用户新指示覆盖原附件的正常无回波规则

在ground01失败之后，用户明确要求：“超声波读不出数据时可认为前方障碍无限远，此时不应该应急停机。”这是一条**后续用户指示**，覆盖附件原先将所有无回波视作无效停车的规则；不是回改历史E4结果。用户同时描述该次约75°后前方为空旷方向、尚未放恢复回波的纸板，这个场景描述与原始`4000/valid=false`板上记录分别保留，不假称测得了原始ECHO电气波形。

E5候选用现有J3实现以下有限分类：仍每100ms发起一笔测距；旧range驱动约23.3ms到量程上限后，不立即把正常长脉冲当故障，而在本次确有TRIG/回波过程的前提下等待实际ECHO回低。**长脉冲完整结束且在80ms事务期限之前**，发布`distanceMm=4000,distanceValid=true`，表示FAR/超量程哨兵，供正常控制继续使用；它不是“实际测得4米”，也不是角度或四周无障碍证明。达到80ms期限、没有有效触发/上升过程、恒高不回低、过短异常等仍发布无效；过期检查保持。≤250mm危险停止、≥300mm连续三个新安全样本后恢复、真实IR锁存/释放，以及350/500mm停靠分段没有取消。

`memberCBoard`仅在d距离页、valid且4000时显示**FAr**（右四位为blank/F/A/r）；invalid4000继续空白，不影响H/L遥控页。`tools/chassis_debug.py`新增`distanceFar`与`distanceKind=FAR/MEASURED/INVALID`：先判断valid，故历史E4的invalid4000仍解码为INVALID。该显示/字段是分类说明，不伪装成真实4米读数。后续静止实测已确认正常空旷场景发布valid FAR且d页显示FAr；运动中的正常远距继续与真正异常仍停车的实机覆盖仍待完成。

### E5方向聚焦回归与尚未完成的发布门

| 项目 | 实际结果 | 日志/边界 |
|---|---|---|
| 当前控制/真实UART定向回归，生产TURN_SIGN=−1 | **269检查PASS**；20条完整UART，low4/high2、straight5、zero9 | `turn_e5/control_negative.log`；覆盖SEARCH、低/高U完整左右字段、U109/110/130/131边界、粗/细前进不变及STOP完整零 |
| 同bench显式TURN_SIGN=+1泛型对照 | **269检查PASS**；20条完整UART | `turn_e5/control_positive.log`；不是把旧符号当E5生产默认，也不把两次269累加成538个独立需求 |
| 编译及以上两次ModelSim运行 | **3.367385秒** | `turn_e5/control_run_metrics.json` |
| 固定25fps真实像素管线→C→UART，显式E5负参数 | **12帧/12报告PASS**；SEARCH41、低U18、前进39、高U34、zero118条报文 | `turn_e5/pixel/run.log`；原RGB565文件与U80→120→160的12帧像素平移顺序未改，无强迫内部报告/健康位 |
| 上述pixel-only Verilator5.050 | 编译12.529247秒、运行71.835396秒、总**84.364643秒** | `turn_e5/pixel/compile.log`、`metrics.json`；这是聚焦RTL_SIM，非真实相机/车辆结果，也不是完整R6 |
| 独立J3引脚时序仿真（完整生产量程驱动/guard） | **46检查PASS，12个输出样本、11次TRIG**；编译5.821181秒、运行83.748601秒、总**89.572575秒** | `sonar_guard_verilator_20261104T133057_380747Z/result.json`、`simulation.log`；真实时钟尺度的模拟ECHO输入，不是实物传感器或完整R6 |
| 独立J3代表事务仿真（显式`+R6_REPRESENTATIVE`） | **25检查PASS，6个输出样本、6次TRIG**；编译5.834637秒、运行38.076932秒、总**43.912875秒** | `sonar_guard_representative_20261104T133440_446720Z/validated_result.json`；完整46检查路径仍保留，此项不单独证明完整R6 |
| E5首次完整干净副本R6 | **FAIL，303.500928秒，targetMet=false**；12项PASS，reader编译到总期限，mutant未运行 | `build/member_b/20261104T133634_057221Z_verilator_course/result.json`；保留首轮失败，不由下一行成功覆盖 |
| E5最终完整干净副本R6 | **PASS，239.403059秒，13 PASS + 1 CAUGHT，targetMet=true**；61个新复制源文件、jobs4 | `build/member_b/20261104T140614_115616Z_verilator_course/result.json`；独立pixel/sonar及continuous/overload并行，285/300秒标准未改 |
| E5 Full Compilation、资源与时序门检 | **PASS，1173.143秒+25.799秒**；ALM29507/32070，setup/hold最差+2.089/+0.116ns，88项报告检查、未约束0 | `build/member_b/20261104T134331_185490Z_build/result.json`、`timing.json`；新SOF6706157bytes，本版原始产物已下载 |
| E5 SOF下载及版本读回 | **PASS，2026-11-05 01:11:16.707754 AEDT** | `program_e5_console.log`；programmerSucceeded/buildIdVerified均true，读回E7070005 |
| E5零速视觉与正常空旷FAR实测 | **8/8蓝1健康锁定，6/6 valid4000/FAR/noHold/zeroSent** | `e5_zero_scene_01.json`、`e5_far_01.json`；用户确认d页far，全部VISION_ONLY未ARM；不等于运动转向或三圈通过 |

表中未以`build/`开头的路径均以`build/remaining_20261104/`为前缀。超声专项覆盖24/39/75ms长脉冲结束后FAR、80ms仍高后无效、晚落沿不补发有效样本、未触发/无上升异常、正常近距及后续新事务恢复；不用方向269项替代它。首个独立超声调用`sonar_guard_verilator_20261104T133013_823304Z/result.json`仍保留编译失败（exit255、0.233933秒）：make/MSYS工具报告权限相关基础设施异常，尚未运行RTL仿真；随后新目录、新源码副本才得到上述PASS。两次不混成无失败的一次运行。代表事务调用的原`result.json`另保留包装器FAIL：包装器旧规则要求bench名称后紧接checks，而新PASS行先写scope。实际编译/仿真均退出0、记录25检查PASS，无需重跑；`validated_result.json`明确只修正结果解读，不删除原FAIL，也不把代表事务等同完整46项边界测试。

首次正式E5 R6使用Verilator5.050、新源码副本、jobs4、285秒目标及300秒总期限，共13个正式bench加故意坏模块检测。已完成的12项依次为pixel-to-UART、control、CCTL、red2Start、sonar代表事务、continuous、overload、HSV、tracker、fixedSheet、colourSampler、markerQueryStore；`mainColourSupportReader_tb`在编译阶段达到总期限，报告`compilation failed or exceeded the complete-suite deadline`，最后清理使墙钟总计303.500928秒、退出1。故意坏模块没有运行，不能记CAUGHT，也不能把12项PASS写成全部功能断言通过。完整原始结果保留，不被后续重试覆盖。

随后只调整主机执行顺序，让独立pixel与sonar仿真并行；原continuous/overload并行保留，不删除13项、输入或断言，不放宽285秒目标/300秒门槛，不借用前一轮二进制。E5完整编译结束后才启动优化R6，避免两者争用资源。该轮实际于`build/member_b/20261104T140614_115616Z_verilator_course/result.json`记录PASS、239.403059秒、targetMet=true：13个正式bench全部PASS，故意提前锁定的tracker mutant为CAUGHT；61个新复制源文件、cleanBuild=true、jobs4。控制台记录`build/remaining_20261104/r6_e5_parallel_console.log`。这是实际完整结果，不把独立聚焦耗时相加估算；生产RTL、TB、runner与测试输入均冻结。

### E5 Full Compilation与post-fit实际完成

本次`build/member_b/20261104T134331_185490Z_build/result.json`记录build ID **E7070005**、顶层`echo7IntegratedTop`、Quartus Prime Lite18.1.0 Build625，状态PASS、退出0。完整编译**1173.143秒**，独立post-fit门检**25.799秒**；`compile.log`报告**0 errors、92 warnings**。结果完成时间2026-11-05 **01:03:31 AEDT**，不是程序下载时间。

实际Fitter为**ALM29507/32070（92%）、寄存器40957、M10K357/397（90%）、DSP51/87（59%）、memory bits2802640/4065280、PLL2/6**。SOF路径为该build目录下`source/quartus/output_files/PartBDebug.sof`，**6706157 bytes**。仅生成SOF本身不表示已装载；后续实际下载及版本读回另列在下节。

已逐项读取本次`timing.json`和result中的`timing.reportGate`、`synchroniserCoverage`，没有套用E4数字。四角分别是slow1100mV0°C/85°C、fast1100mV0°C/85°C，setup/hold/recovery/removal共16个角点摘要均非负；最差setup **+2.089ns**、hold **+0.116ns**。报告门实际分析**88项检查**；Illegal Clocks及所有列出的未约束clock/input/output port/path计数均**0**。

CDC逐角覆盖：writeGray/readGray/timeGray的9/9/32位都有实际timed path，falsePathCount为0，对应同步级setup/hold覆盖均完整；resultToCamera1589位、requestCdc22位保留setup路径，resultToDisplay979个物理端点覆盖完整。四角max-skew、net-delay约束均通过，最差裕量分别**18.013ns、13.647ns**。每角预期与报告同步链均**63条**、coverageStatus=PASS；MTBF数值验收明确为**NOT_ASSESSED**，不把报告中的估计值当成完整可靠性验收。时序/CDC通过不替代优化R6、实际下载或E5机械闭环。

### E5实际下载、零速视觉与空旷FAR确认

`build/remaining_20261104/program_e5_console.log`记录使用上述成功build的原始SOF执行实际下载：status=PASS、programmerSucceeded=true、buildIdVerified=true，读回**E7070005**。完成时间为UTC **2026-11-04T14:11:16.707754**，即AEDT **2026-11-05 01:11:16.707754**。这与01:03:31的构建完成是两个独立事件；未用旧E4读回或发布副本的存在替代本次下载。

下载后只读观察均通过同一会话分别冻结CCTL/BCTL；“配对”不表示C/B在完全相同的时钟边沿冻结，也不表示每次主机轮询都是新的超声采样。下列日志以`build/remaining_20261104/`为前缀：

| 记录 | 实际观察 | 证据范围 |
|---|---|---|
| `e5_zero_scene_01.json` | 3.045175秒、8/8完整配对，C/B各8个不同帧；蓝1全部healthy/observed/locked，U170、V159–160，实际J3均432mm有效 | E5、VISION_ONLY/IDLE、未ARM、无motionPermit、L/R0、zeroSent=true、无HOLD；实际红24/蓝16、配置1、colourCalibrated=true，scanCalibrated=false |
| `e5_far_01.json` | 用户移开挡板后2.270134秒、6/6完整配对，C/B各6不同帧；全部distanceMm4000、valid=true、distanceFar=true、distanceKind=FAR，sonarHold=false | 用户同时确认实物d页显示far；全程VISION_ONLY未ARM、L/R0、zeroSent=true；健康无目标帧observed/locked=false，不能写成目标一直锁定 |

两组历史faultFlags=3仍保留，当前健康不受该历史值永久阻断；没有伪造J3或注入距离。第二组验证正常空旷场景得到FAR分类及显示，4000仍是超量程哨兵，**不是测得4米或原始ECHO波形记录**。全程本来未ARM，不能据此声称运动被保护停下、FAR期间已连续旋转、实际转向已纠正或整车落地闭环通过。此时板上E5保持VISION_ONLY/未ARM/零速，新版三次完整圈数仍**0/3**，首圈仅准备执行；没有写入scanCalibrated。

### E5冻结源码变更索引与验证边界

| 文件/范围 | 本轮作用 | 已有证据与剩余边界 |
|---|---|---|
| `rtl/top/echo7IntegratedTop.sv`、`rtl/common/memberBBuildId.svh` | 默认TURN_SIGN=-1，设计身份E7070005；直行左右极性不变 | 控制正/负参数、像素到完整UART回归；实际转向待新SOF |
| `rtl/member_c/sonar_guard.sv` | 在有界事务内等真实长ECHO回低后发布FAR，故障仍invalid；防旧事务状态影响新周期 | 完整46检查及代表25检查；真实空旷传感器波形尚未测得，不能据仿真宣布新硬件通过 |
| `rtl/member_c/memberCBoard.sv`、`tools/chassis_debug.py` | valid4000距离页FAr及FAR/MEASURED/INVALID主机分类 | invalid4000仍无效；显示不是实际4米测量，也不改保护阈值 |
| `tests/member_c/tb_control_repair.sv`、`tests/integration/tb_pixel_uart_repair.sv`、`tests/member_c/tb_sonar_guard.sv` | 方向边界、完整左右JSON及真实时钟尺度TRIG/ECHO测试 | 固定像素输入保留；引脚波形是仿真输入，不能充当实物传感器结果 |
| `tests/rtl/manifest.json`、`tools/lib/verilator_suite.py`及对应主机测试 | 新增sonar代表项进入13项R6；主机执行调度优化 | 首次完整运行超时FAIL；优化后完整13项+mutant通过，主机测试不累加为独立RTL断言 |

当前生产RTL、TB、runner和输入均已冻结，只继续整理文档与实际结果。任何产物都须单列实际源码副本、工具结果和下载身份，不能因源文件已写E5或已生成SOF就认定板卡已更新。

后续单圈脚本另存为`ground_scan_trial_e5.py`，保留E4原脚本及ground01日志。它先只读验证BCTL版本确为E7070005，再准备健康无目标合成源；新SEARCH检查(+4,−4)，允许已确认valid FAR，仍由每次fresh ARM开始一次任务、实际IR A终止，故障或中断记录为无效，不自动解除IR或写calibrated。真实视觉观察脚本`integrated_task_observer.py`不注入、不心跳、不发START，等待实体POWER，仅记录一个任务的状态/距离，DOCKED零速保持3秒与NOT_FOUND分开；该真实视觉观察脚本随后已运行E5蓝1落地任务，但以NOT_FOUND结束，详见后节。E5单圈脚本随后执行三次，均取得板上计时与用户满圈观察，已设置13.6秒经验参数，见以下逐轮记录。六车位地面闭环、正常/旁路各三次地面对照、实际停车误差和端到端机械响应测量均待完成。

### E5地面首轮：逆时针满圈，保留约10°超转及3.5cm前移

`build/remaining_20261104/ground_e5_01.jsonl`记录塑胶地板、当前整车/底盘供电、健康无目标合成帧和真实J3/IR/UART；临时预算60秒、scanCalibrated=false。结果为**IR_TERMINATED_TIMING_CAPTURED**，总主机观察34.960365秒、197个C快照，failure为空、cleanupErrors为空；这不是自动宣告精确360°校准PASS。

80个运动快照全部为CHASSIS_INJECT/SEARCH，逻辑(+4,−4)，ARM/permit/sourceHealthy/leaseValid为true；选择蓝1、tag4、配置1不变，无HOLD、无效测距、fatal或提前IR。70次快照为实际MEASURED **377–3120mm**，10次为**4000/valid FAR**；FAR分为2/1/7次三个采样段，最长连续采样首末跨度1.072009秒。这里计数是CCTL快照，不能称10次独立超声采样；它支持本轮存在FAR时仍获准SEARCH且未因FAR进入HOLD。80个不同合成帧；相邻79对运动快照的timeUs增量与scanElapsedUs增量差为−1至+1μs，没有观察到扫描计时中断。

IR终止快照在主机34.905592秒，读回IR锁存、IDLE、未ARM、L/R0、zeroSent=true，累计获准SEARCH时间 **13.561176秒**。脚本随后才发主机STOP（34.905637秒）及VISION_ONLY（34.910985秒）；最终34.960285秒仍为VISION_ONLY/IDLE、未ARM、零速发送完成，IR保持锁存，J3为379mm有效。该先后顺序证明板上IR撤销先于清理命令，不把主机轮询间隔当作IR或机械停车延迟。

用户先报告：“**转满一圈多一点点，同时转完后相较于起始是往前了一些**”，随后明确补充：“**逆时针，多了大概10°，前移约3.5cm。第二圈就绪**”。`ground_e5_operator_notes.json`保留两条原话；本轮实际俯视逆时针，约超转10°、前移约3.5cm，误差是用户估计，不能改成精密测量或声称原地无漂移。13.561176秒是本次IR终止前的命令累计时间，含人为终点判断及尚未分离的机械响应，不当成精确360°时间，也不据此反推角速度或自动写入永久参数。截至首轮阶段，物理满圈已确认**1/3**，后续第二/三轮记录另列；板上收尾VISION_ONLY/未ARM/零速、IR锁存。发布副本已按E5身份复制到`firmware/E7070005/PartBDebug.sof`（6706157bytes），实际下载仍以上述原始build记录为准。

### E5地面第二轮：满圈11.075500秒，约5°超转/2cm前移及启动不对称

`ground_e5_02.jsonl`记录相同塑胶地板/整车供电条件、回到起始位置/朝向并整理线缆后执行一轮。总主机观察27.025306秒、146个C快照，结果IR_TERMINATED_TIMING_CAPTURED，failure为空、cleanupErrors为空，scanCalibrated未写入。

66个运动快照均为不同合成帧、SEARCH逻辑(+4,−4)、ARM/permit/source/lease健康；选择蓝1、tag6/配置1保持，J3均valid，无HOLD/fatal/提前IR。53个MEASURED快照395–1686mm，13个FAR快照分2/5/6次三段，最长采样首末0.751414秒；不把主机采样数当独立测距次数。相邻65对运动快照timeUs与scanElapsedUs增量差−1..+1μs。

主机26.981585秒的IR快照已IDLE、未ARM、IR锁存、L/R0、zeroSent=true，累计SEARCH **11.075500秒**，J3393mm有效；随后才发STOP（26.981632秒）及mode1（26.987079秒）。最终27.025238秒VISION_ONLY零速、IR仍锁、404mm有效。板上记录完成后，用户确认：“**满一圈，多5°，前移大概2cm。然后我发现主要是启动的时候左右轮动力输出不均匀，都出现了单边前冲的情况**”。据此第二圈可计为实际满圈，累计**2/3**；约5°和2cm仍是用户估计，不是精确角度闭环或位移传感器测量。保留它与第一圈不同的实际时间，不以期望值修正日志或预填平均参数。

用户观察到两轮启动均有单边前冲/动力不对称。该现象必须保留，不能据此声称同转速命令必然同步起步，也不能仅凭观察认定UART左右字段、实际接线、电机、机械摩擦或电源中的某项已被证实为根因。当时只读核对命令链，未为掩盖漂移修改像素、左右命令或日志；第二轮结束时尚未写入scanCalibrated，后续第三轮及参数写入另列。

### E5第三轮满圈及13.6秒有界搜索参数实际设置

`ground_e5_03.jsonl`已完成IR_TERMINATED_TIMING_CAPTURED，主机总27.078186秒、151个快照，累计SEARCH **11.436358秒**，failure为空、cleanupErrors为空，未写标定。70个不同帧运动快照全部SEARCH、(+4,−4)，source/lease/ARM/permit/J3valid保持，蓝1/tag8/配置1不变，无HOLD/fatal/提前IR。55个MEASURED快照402–1689mm，15个FAR快照分2/5/8次三个窗口，最长采样首末1.175691秒；69对相邻运动快照计时增量差−1..+1μs。IR在主机27.023622秒已撤ARM、IDLE/左右0/zeroSent=true，J3423mm有效；随后主机STOP27.023663秒、mode1 27.029069秒。末27.078123秒VISION_ONLY/未ARM/零速、IR锁、432mm有效。随后用户明确：“**满圈，我按晚了，多转45°，没有单侧前冲**”。第三轮物理满圈成立，累计**3/3**；约45°超转包含用户明确报告的按A较晚因素，第三轮未见起步单侧前冲，位移未提供，不补猜。第2/3轮命令与首轮相同，但用户没有在这两次回复中分别重述旋向。

三次板上累计时间分别13.561176、11.075500、11.436358秒，范围差**2.485676秒**、均值12.024345秒、中值11.436358秒。均值与中值分别比已测最大值少1.536831、2.124818秒，不能据这三条记录保证它们覆盖较慢轮次；起步单边前冲、用户IR终点判断及真实地面差异均未单独量化。

**已实际设置：**在三轮满圈均确认后，将最大已测命令累计时间向上取整为**13.6秒（13600000μs）**，作为当前塑胶地板/整车/底盘供电条件下覆盖这三次记录的有界SEARCH上限。它只比已测最大多38.824ms，属于有限样本下的经验上限，不能保证未来所有圈都完成，也不能称精确360°控制；较快轮次继续运行到该上限可能多转。保留原始时间/约角度/位移，不按约10°或5°比例缩放后冒充精密标定。`e5_scan_calibrated_13600ms.json`是实际CLI输出记录，读回scanBudgetUs=13600000、scanBasis=CALIBRATED_TIME、scanCalibrated=true；当时VISION_ONLY/IDLE、未ARM、左右0、zeroSent=true、IR仍锁，真实J3421mm有效。设置过程没有START，旧scanElapsed11436358是上轮保留计数，不是新任务已运动。运行时参数跨普通mode切换保留，reset/重下载清回10秒未标定默认；它没有烧成永久参数。固定13.6秒预算自动终止时的实际转角/停车误差尚未验收；后续真实蓝1任务已执行，但没有DOCKED，结果另列。

启动不对称的只读源码审查：`memberCBoard.sv`启用`chassis_command`的`USE_WHEEL_REQUESTS=1`；`chassis_command.sv`在同一IDLE时钟沿用当前left/right生成完整`wheel_msg(...)`并整体装入`shreg`，SEND只逐字节移出该冻结报文。左右字段属于同一个JSON，不是每侧单独取旧值再拼接。现有完整UART回归也核对过左右字段；这能排除该源码路径的逐侧旧值拼接解释，**不能证明对端解析/电机同时施力，亦不能替代实际电气波形、轮速或机械响应测量**。没有据此清除用户报告的单边前冲现象。

## E5真实蓝1任务失败与固定目标短转诊断

### POWER启动的真实搜索任务未完成停靠

`build/remaining_20261104/integrated_blue1_01.jsonl`是REAL_CAMERA/真实J3/INTEGRATED任务。原label为`blue1_visible_left_floor_01`；用户在独立preflight之后明确把蓝1移出视野，实际START前是健康NOT_FOUND。原日志label不重写，场景更正在`integrated_e5_operator_notes.json`单独保存。由用户实体POWER启动，主机START、合成观察写入、heartbeat均**0次**，没有把合成链路当真实视觉。

结果为**NOT_FOUND_OBSERVED / SCAN_BUDGET**，不是DOCKED或停靠PASS。完整观察73.006122秒、656个C快照；首次ARM至终态的主机观察36.330141秒，任务段335个不同C帧快照（334次ARM加终态）。全程任务模式INTEGRATED/REAL_CAMERA、蓝1、tag10、配置1稳定，leaseValid=false；J3均有效、无sonarHold、无IR、无fatal，历史faultFlags3保留。有效距离379–4000mm，其中14个FAR快照；这次终止不是无效测距或租约掉线。

| 以首次观察ARM为零点 | 板上事件与意义 |
|---|---|
| 约+1.200秒 | **首次ACQUIRE**，累计SEARCH约1.111837秒；第一次目标观察触发停转，但未完成新边界后的确认，约+2.320秒回SEARCH。不能写成11秒后才首次发现目标 |
| 约+12.637/+12.970秒 | 后续ACQUIRE/首次ALIGN，开始对已确认目标纠偏；它是后续成功确认，不是首个发现事件 |
| 随后约19秒 | 反复ALIGN、短暂APPROACH、LOST和重新ACQUIRE；搜索累计保持11.205106秒，ALIGN不冒充SEARCH计入预算 |
| 约+32.643秒 | 目标继续丢失后回SEARCH，消耗剩余搜索预算 |
| 约+35.171秒 | 累计SEARCH达到13.600000秒，进入最后一次静止ACQUIRE |
| 约+36.330秒 | 最后确认超时，NOT_FOUND/SCAN_BUDGET、未ARM、L/R0、zeroSent=true；主机随后才STOP及切VISION_ONLY，cleanupErrors为空 |

任务段状态快照为SEARCH128、ACQUIRE49、ALIGN129、LOST23、APPROACH5、NOT_FOUND1。8个连续LOST窗口内采样时源健康仍true；ARM期间仅5个源不健康快照，所见输入年龄38.918–91.242ms，未见超过150ms年龄界限。ALIGN左右逻辑方向分别65/64个快照，APPROACH只有5个+5/+5快照、距离613–663mm，未见细速接近或DOCKED。CCTL未保存逐帧U及B拒识原因，不能仅凭这些数据把所有丢锁归咎于候选溢出、图像模糊、越界或机械过冲中的某一个原因。

用户实物反馈原话：“它最开始逆时间扫描的时候，忽略了，在第二次扫过的时候才确认到。然后跟踪靠近了一段时间后，突然逆时针转动，使得蓝一超出范围”；随后确认“前面正确，然后，左右来回一段时间后，转远了”。这与日志中的首轮确认失败、后续反复纠偏和丢锁相符。该失败保留，不能因为有13.6秒有界终止和零速收尾就把整机停靠标为成功。没有测得精确停车距离、物理停止延迟或像素到UART延迟。

### 固定蓝1短转：方向趋向中心但跨越中心，自动诊断仍为INCOMPLETE

`real_turn_probe_e5_01.jsonl`仅执行一次主机START，真实蓝1/J3，无注入和heartbeat；开始前3个合格帧U均57。START发送到STOP请求实际**0.340987秒**，不是严格0.30秒机械脉冲；7个运动C快照均为真实ALIGN逻辑(+4,−4)。STOP及VISION_ONLY后首先验证的零速状态FPGA timeUs为**1542683620**，但zeroSent仅证明零速JSON发送完成。

| 零速确认之后的新图像capture时间 | frame / U | 锁定 |
|---|---|---|
| +245.133ms | frame38591 / U96 | true |
| +525.021ms | frame38598 / U142 | false |
| +884.877ms | frame38607 / U169 | true |

后3帧只有2帧满足锁定资格，脚本如实输出**INCOMPLETE**、medianDeltaU=null、trend=UNAVAILABLE、cleanupErrors为空，不能改为三帧中值PASS。上表是新采集时间，不把约48–49ms处理耗时或旧管线报告误当作采集延迟。随后`e5_turn_probe_settled.json`的6个静止帧U全173、全部健康锁定，但这些帧在零速确认约**90.489–92.608秒**后采集，不能证明1.5秒内已经停稳。

用户确认纸板始终固定、最终车轮已完全停止；对于车身短促启动后是否继续转动，回答“不是很确定，因为没法判断”。固定目标的U从57趋近并越过中心120，支持E5有效方向正确且存在明显过冲的判断；它**没有测出尾转持续时间或机械停稳时间**。200ms之后新采集画面仍在变化，不适合继续把200ms当作已证实的稳定等待；后续采用1.5秒是保守设计配置，尚未获得1.5秒机械停稳的实物证据。

## E7070006：分档短转与停止后重新确认，构建时序未通过

E6在保留E5搜索方向和FAR规则的基础上，只调整ALIGN运动调度。用户追加建议可通过速度控制后，采用以下实际实现；没有修改像素、目标坐标、TURN_SIGN或直行左右极性。

- 进入ALIGN时锁存当前方向、速度和脉宽，不由后续报告刷新起点。误差为`abs(U-120)`；在110–130死区外，误差≤30像素用**3cm/s**，>30用**4cm/s**。SEARCH仍连续4cm/s，不随ALIGN降速。
- 脉宽为`clamp(误差×2000μs, 20000μs, 100000μs)`；例如U89为62ms/4cm/s，U90为60ms/3cm/s，U109/U131为22ms/3cm/s。到期、跨到对侧或转动后进入中心都先输出零速并进入既有ACQUIRE，不在同一脉冲直接反向，也不刚转中就立即平移。
- ACQUIRE等待完整零速JSON的`zeroSent`，然后等待**1500000μs**，再发新的target fence，只接受之后的新capture，连续3帧锁定后重新判向。900000μs新帧确认超时不变。只有进入ALIGN时已经居中、此次没有旋转的路径可转APPROACH；所有ALIGN入口均锁存本轮参数。
- LOST持续无目标时仍按原300ms策略回SEARCH，HOLD退出也沿原恢复路径；**不是所有丢失分支都强制等待1.5秒**。安全/STOP/IR/租约取消优先，搜索累计时间、13.6秒运行时预算和120秒任务总限不会被每次短转重置。

逻辑脉宽不是实际车轮PWM/旋转时间。短脉冲会增加起步次数，可能放大已观察到的单边前冲，3cm/s在当前底盘上能否可靠起转尚待实测；1.5秒也不等于已测得物理静止。因此E6是针对现场证据的候选修正，不声称已解决机械过冲、漂移或成功停靠。

| E6项目 | 实际状态与证据 |
|---|---|
| 生产文件 | `motion_fsm.sv`、`member_c_control.sv`增加分档/锁存短转；`memberCBoard.sv`默认驻留同步改1.5秒，build ID为E7070006；生产源码已冻结 |
| 控制与完整UART聚焦 | ModelSim正/负TURN_SIGN各**338检查PASS、53完整UART**（spin32、drive4、zero17，粗low24/high1、细low6/high1），编译0 error/0 warning；编译加两仿真**5.2128905秒**。`control_e6_20261104T144617Z/`，不把两次338累加为676个独立需求 |
| 控制定向覆盖 | 100ms上限、近中短脉冲、误差30/31的3/4cm/s分界、两侧完整±0.03 JSON、同侧新U不延长/不改速、跨侧先停、zeroSent后驻留/新fence/三帧、转中先停后前进、SEARCH>100ms连续、原安全/红2/坏帧恢复/预算。TB驻留1500μs是加速协议测试，不冒充生产1.5秒或机械停稳 |
| 固定25fps真实像素到UART聚焦 | **14帧/14报告PASS**，新副本、sourceUnchanged=true；UART search41/left18/forward19/right34/zero178。编译9.217031秒、仿真69.766992秒、含包装器总**78.991060秒**；`pixel_uart_e6_20261104T144702_631205Z/result.json` |
| 像素测试必要适配 | 仅将居中画面从2帧保持为4帧，原12帧及其顺序、固定25fps、像素文件和全部断言保留；新增2帧为停止边界后的三新帧资格提供足够时间，没有缩减资格或伪造锁定 |
| E6完整R6 | **PASS，266.840318秒、13 PASS + 1 CAUGHT、targetMet=true、退出0**；61个新复制源文件、cleanBuild=true、Verilator5.050、jobs4，满足285秒目标/300秒门槛；`build/member_b/20261104T144856_668139Z_verilator_course/result.json`，不沿用E5的239.403059秒 |
| E6 Full Compilation验收 | **FAIL，不得下载**；`build/member_b/20261104T144730_277631Z_build/result.json`。compile工具退出0、1183.703秒，但整体验收因critical timing warnings退出1；该记录没有执行独立timing_gate步骤，不记四角门检PASS |
| E6实际拟合/时序 | ALM29462/32070、寄存器41136、M10K357/397、DSP53/87、存储2802640bits、PLL2；CLOCK_50 slow85 setup −0.265ns/TNS −1.786ns，slow0 setup −0.203ns；最差hold +0.120ns。器件装得下不等于时序通过 |
| E6下载及实物 | **未执行，失败产物不下载**；当时设备仍E5、VISION_ONLY未ARM/零速；不得把本节仿真写成实机修复成功 |

表中简写日志路径以`build/remaining_20261104/`为前缀。E6功能仿真通过与编译时序失败分别记录，没有通过改seed、放宽SDC或忽略critical warning来接受该产物；后续算术修正为E7。

## E7070007：等价缩窄脉宽运算，独立构建/时序/下载通过

### E6失败定位，不把诊断命令退出0当作时序PASS

对E6既有拟合数据库只读运行Quartus STA，日志位于`build/remaining_20261104/e6_sta_diagnosis_20261104T150928_837210Z/`，总**13.098885秒**、工具退出0，但`result.json`明确`timingPass=false`。两个slow角各取20条最差setup路径，都从`mode[0]`到`alignPulseUs`低位寄存器：模式选择报告capture时间，经adapter的afterFence减法/比较及centreU即时旁路，进入32位绝对误差、两级DSP乘法、clamp比较及寄存器装载。85°C最差路径有15级逻辑、data delay19.971ns；两段DSP延迟分别3.159/2.047ns。完整起终点和逐段延迟保留在`path_endpoints.tsv`及两个`setup_6_slow_1100mv_*_worst20.txt`，定位依据是实际路径，不是看到DSP增加便推定根因。

### 只改变表示宽度，保留实际控制行为

E7在`motion_fsm.sv`为五个默认参数（deadband110/130、2000μs/像素、最小20000μs、最大100000μs）增加等价运算分支：实际误差先以8位表示，最大135；脉宽专用误差限制到10..50，再以6位输入扩展到17位，计算`(x<<11)−(x<<5)−(x<<4)`，即2000x，居中输出仍为0。最大中间项102400小于17位上限，减法不会负值；最终20000..100000μs与旧公式相同。3/4cm/s速度分档仍使用**未截限的实际误差**；非默认参数沿用原通用公式。

没有改adapter即时撤权/fence、安全优先级、SDC/QSF、TURN_SIGN、SEARCH、速度档位、脉冲时间或1.5秒生产等待；版本标识改为E7070007。该改法旨在缩短已定位的运算链，是否满足拟合时序只能由E7独立结果决定，不能以算术等价枚举代替STA。

| E7验证/发布步骤 | 当前事实 |
|---|---|
| 首次编译失败 | `control_e7_20261104T151306Z/`保留**COMPILE FAIL**：带基数十进制常量紧接三元`?`被ModelSim词法分析成错误数字；5 errors/1 warning，仿真未启动。只补必要空格，没有改算法；不删除失败或改成首跑通过 |
| 默认运算枚举 | U=0..255共256种输入，新旧脉宽**0处差异**；`control_e7_20261104T151338Z/arithmetic_equivalence.json`保留逐U数据。此项是算术等价证据，不是机械时间或post-fit证据 |
| 控制/UART回归 | 新目录`control_e7_20261104T151338Z/`编译0 error/0 warning；负生产参数及正泛型参数各**338检查/53完整UART PASS**（spin32、drive4、zero17，粗low24/high1、细low6/high1），编译加两仿真**5.113292秒**，结果关联此前词法FAIL；没有累加正负检查当成独立需求 |
| E7正式R6 | **PASS，265.276162秒、13 PASS + 1 CAUGHT、targetMet=true、退出0**；61个新复制源文件、cleanBuild=true、Verilator5.050、jobs4，满足285秒目标/300秒门槛；`build/member_b/20261104T151442_166532Z_verilator_course/result.json`。完整14帧pixel在本轮正式套件中独立验证，不沿用E6二进制或R6结果 |
| E7 Full Compilation | **PASS，1147.755秒；post-fit门检PASS，26.087秒**，0 errors/92 warnings；`build/member_b/20261104T151422_461823Z_build/result.json`。ALM29320/32070（91%）、寄存器41015、M10K357/397、存储2802640bits、DSP51/87、PLL2。只使用本版实际拟合结果 |
| E7时序/CDC门检 | 最差setup **+0.864ns（slow0）**、hold **+0.117ns**；88项报告检查，Illegal Clocks及各类unconstrained均0。四角所需同步链均63/63、coverage PASS，MTBF NOT_ASSESSED；Gray 9/9/32全路径、相机/请求payload1590/22与显示979物理端点完整覆盖。max-skew约束最差slack +18.437ns、net-delay约束最差slack +13.942ns，不把裕量写成实际skew/延迟 |
| E7下载身份 | **PASS**；原始`build/member_b/20261104T151422_461823Z_build/source/quartus/output_files/PartBDebug.sof`为6706155bytes。`program_e7_console.log`确认programmerSucceeded/buildIdVerified=true、退出0，结束UTC2026-11-04 15:34:42.428181，即2026-11-05 02:34:42.428181 AEDT |
| E7零速准备/实物任务 | observer01窗口内未ARM、INCOMPLETE；后续用户KEY0报告另列。observer02已ARM，261C/258B快照，缠线/近距HOLD后达60秒观察限、INCOMPLETE，末VISION_ONLY未ARM/零速。真实落地DOCKED及机械改善仍PENDING |

表中控制测试简写路径以`build/remaining_20261104/`为前缀。历史E5失败/INCOMPLETE、三圈超转与启动不对称、E6时序失败及E7首次词法FAIL均保留；当前没有把分档短转写成实物停靠成功。

`build/remaining_20261104/e7_scan_calibrated_13600ms.json`保留下载后实际参数恢复读回：scanBudgetUs/remaining=13600000、scanBasis=CALIBRATED_TIME、scanCalibrated=true、scanElapsed=0；VISION_ONLY/REAL_CAMERA、蓝1稳定独热选择、sourceHealthyFresh=true、targetObserved/Locked=false、未ARM、左右0、zeroSent=true、IR=false、sonarHold=false、J3694mm/valid MEASURED。用户确认塑胶地板及供电条件未变，因此恢复E5三圈获得的经验参数，没有重新宣称精确360°；下载使运行时参数清回默认，恢复是明确的新写入。该操作没有启动任务，真实搜索及机械效果待后续独立记录。

### E7首次真实观察：POWER窗口到期，未发生任务启动

`build/remaining_20261104/integrated_blue1_e7_01.jsonl`结果为**INCOMPLETE**，原因`start window expired; late authorization is cancelled`。45秒POWER等待窗口内未出现ARM，含收尾共147个CCTL快照均IDLE/零速，首次ARM/终态时间及任务观察时长均null；完整观察含收尾45.112171秒，主机START/合成写入/heartbeat均0。脚本到期取消迟到授权并STOP、切回VISION_ONLY，最终未ARM、左右0、zeroSent=true、cleanupErrors为空。这是该观察窗口内没有任务启动的记录，**不算运动控制失败，也不算搜索或停靠成功，更不能据此断言窗口外没有运动**。

用户随后明确报告反复按POWER没有反应，又按KEY0两次、每次有短暂运动。此实物反馈保留，与上述窗口内未ARM分开；没有足够记录证明KEY0、延迟IR、视觉事件或其他因素中的哪项导致短暂运动，不推断唯一因果。主机随即设置并验证VISION_ONLY未ARM/零速，B身份仍E7070007；`e7_after_key0_pairs.json`的6组分别冻结C/B读回中5次C源健康，1次实际candidateOverflow/frameGood=false，随后恢复。真实J3先92mm/HOLD，下一792mm仍HOLD，再788mm解除HOLD，其后789–792mm；这些是零速状态观察，不宣称此处完成一次运动急停试验。KEY0将扫描参数清为10000000μs/SCAN_UNCALIBRATED，符合既有复位行为；用户被要求整理手部、线缆及红2后，`e7_scan_restored_after_key0.json`明确恢复13600000μs/CALIBRATED_TIME、零速未ARM、J3737mm有效。没有重编译或更换E7产物。

### E7第二次真实搜索：缠线与近距HOLD，60秒观察限后INCOMPLETE

`build/remaining_20261104/integrated_blue1_e7_02.jsonl`保留**261个CCTL/258个BCTL快照**，结果INCOMPLETE，原因`60 s task observation limit reached during status read`。首次ARM记录为主机20.0387466秒，实际任务观察60.0152787秒，含准备及收尾总80.0976572秒；没有DOCKED/NOT_FOUND任务终态。主机START、合成写入、heartbeat仍均0；真实POWER启动时SEARCH逻辑(+4,−4)、REAL_CAMERA、13.6秒已标定预算、J3738mm有效。

| 主机观察秒数（轮询时间，不是精确状态转换时刻） | 实际状态/距离 |
|---|---|
| 约20.039 | 首次ARM/SEARCH，J3738mm |
| 约21.331→23.701 | ACQUIRE零速确认后未取得目标锁定，返回SEARCH；J3748→805mm |
| 约26.068 | J3215mm有效，进入HOLD/左右0 |
| 约28.728 | J3319mm、sonarHold=false，回SEARCH |
| 约29.598 | J333mm有效，再次HOLD/左右0，累计SEARCH停在4.512126秒 |
| 约80.098收尾 | VISION_ONLY/未ARM/左右0/zeroSent=true，J3251mm仍HOLD，cleanupErrors为空 |

用户实物原话：“**扫过了蓝1，继续转的时候，遇到了线缆缠绕，然后超声波判定到距离过近中止**”。因此本次既不是主任务停靠PASS，也不能归结为纯控制逻辑失败；真实搜索受线缆和近距保护条件影响。记录未见ALIGN/APPROACH，不能以本轮证明新短转策略的实物效果。60秒是主机观察期限，最后STOP是观察器收尾，不是宣称生产120秒任务总限已到或车体精确停车延迟。下一步拟在蓝1居中的场景验证接近停靠，避免再整圈缠线，当前等待用户摆位；源码和通过的构建保持冻结。


## E7后续地面实测与E8连续前进纠偏修复（2026-11-05）

以下全部在用户确认的塑胶地板、底盘供电、同一车身配置下进行，不能外推至实验室环氧地板。原始物理反馈与计数汇总保存在`build/remaining_20261104/e7_operator_notes.json`。E7构建/R6通过不等于这些实际任务通过。

| 实验 | 板上事实 | 用户实物观察 / 结论 |
|---|---|---|
| E7窗口03，`integrated_blue1_e7_03.jsonl` | 140 C / 138 B，45秒启动窗口内无ARM，正常STOP/VISION_ONLY零速收尾 | 用户再次报告多次POWER无反应。没有精确按键/IR接收时间，不把窗口过期推定为遥控器损坏；随后改为已确认就绪后一次主机START，避免人工窗口反复错过 |
| E7真实居中任务04，`integrated_blue1_e7_04.jsonl` | 预检4个不同帧全部锁定U112、J3约699mm；一次主机START，真实相机，无合成写入/续租。206 C / 201 B，观察60.1635664秒；起步APPROACH +5/+5后反复短ALIGN/ACQUIRE，末J3约684mm，未DOCKED，收尾零速无错误 | 用户：向前蠕动，右轮幅度明显更大；整轮左约1cm、右约3.5cm。这是包含最初前进与后续短转的累计估计，不能当作单脉冲轮程 |
| E7真实右侧任务05，`integrated_blue1_e7_05.jsonl` | 预检3/3锁定U197、J3约669mm；一次主机START、15.048011秒限时、56 C / 51 B。U197→193→186→132→123，随后进入APPROACH又移到U80→60→56；无DOCKED，正常收尾 | 用户确认转近了，但主要左轮大幅动作、右轮基本不动，最终蓝1在左1/3。短转有效改变朝向，但未形成可靠停靠；不能把靠近中心的瞬间算完成 |
| 两秒连续直行隔离，`ground_straight_e7_2s_01.jsonl` | **合成居中视觉**经过真实C/J3/IR/UART及500ms注入租约，不是视觉闭环。持续+5/+5，实测距离<500mm后自动+3/+3；J3由618降到循环末454mm，首次零速收尾436mm、随后430mm；STOP/VISION_ONLY未ARM及zeroSent验证 | 用户确认“往前走，我看基本是直的”。这说明本场条件下连续直行可实际推进；不证明差速纠偏已修好，也没有测得轮端编码器速度或起步不均的根因 |

E8由上述实物证据推动，源修改限于APPROACH的控制策略及版本标识，不更改相机识别、轮子正负极性、底盘固件、UART协议、SEARCH速度、旧扫描参数、初始ALIGN脉冲、IR/J3或取消规则：

- U110–130居中死区仍不变，只有完成原有锁定/对准资格才进入APPROACH。已进入APPROACH后，目标在U75–165（中心误差≤45像素）且仍新鲜可靠时，允许两轮同向前进修正，避免微小偏差立即造成两轮反复停启。
- 居中保持原来远距5/5 cm/s、500mm内3/3 cm/s。非居中纠偏使用远距5/3或3/5，500mm内4/3或3/4；生产TURN_SIGN=-1下低U为左快、高U为右快，泛型正号相反。没有将逻辑请求值冒充实测轮速。
- 离开纠偏范围或距离≤350mm但尚未居中，组合输出立即停止前进，进入ACQUIRE：先等完整零速UART，再驻留1.5秒和新采集fence后的三帧资格，之后才允许原ALIGN。消除前进后直接反转一侧的路径。1.5秒仍是保守配置，不是已测机械停稳上限。
- 只有可靠居中且距离≤350mm才DOCKED并解除任务；丢失/坏帧/超时、IR、≤250mm近障、拨码改变、SW9、STOP及注入租约等原门控保留。

上述为E8实现依据，后续本版回归、构建、下载及首次真实蓝1停靠结果分别列于下文。初始ALIGN短脉冲、扫描扫过目标、物理线缆缠绕、不同地面/供电下起步不均仍有实测限制；不以连续直行隔离实验或单次蓝1成功替代六车位真实视觉任务。


E8已完成的定向验证：`build/remaining_20261104/control_e8_20261104T160731Z/`，两种TURN_SIGN各433检查/88条完整UART PASS，编译0错误/0警告，总6.7496263秒；精确5/3和4/3双向JSON、U75/165范围端点与74/166停车边界、501/500/351/350mm距离边界、350mm偏心不前进/不冒认DOCKED、完整零速/驻留/fence后三帧、目标丢失/坏帧/STOP/IR/租约撤销均覆盖。该计数不跨两符号累加成866个独立需求。正式R6目录`build/member_b/20261104T160829_370108Z_verilator_course/`已PASS，270.641086秒、13项PASS + CAUGHT、targetMet=true；干净61源码副本、Verilator5.050、jobs4和最多两个独立仿真。14帧像素到UART结果为14报告、search41、left18、forward19、rightCorrection34（精确3/5向前差速）、zero177、rightSpin0；不将原地右转与新增差速混称。细分左向/近距差速由控制TB覆盖。

### E8独立构建、时序与实际下载

`build/member_b/20261104T160829_127927Z_build/result.json`为本版独立PASS，编译1159.722秒、post-fit门检25.963秒，0 errors/92 warnings。ALM29281/32070（91%）、寄存器41081、M10K357/397、存储2802640bits、DSP51/87、PLL2；最差setup +1.021ns、hold +0.121ns。88项报告检查通过，Illegal Clocks及各类unconstrained均0，四角所需同步链63/63、coverage PASS，MTBF仍NOT_ASSESSED；不继承E7数值。

原始SOF为该build目录下`source/quartus/output_files/PartBDebug.sof`，6706156bytes。`build/remaining_20261104/program_e8_console.log`记录programmerSucceeded/buildIdVerified=true、退出0，结束UTC2026-11-04 16:28:58.446132，即2026-11-05 **03:28:58.446132 AEDT**，实际读回E7070008。发布副本`firmware/E7070008/PartBDebug.sof`（当时发布副本，后由E9替换）与原SOF逐字节一致；旧E7发布副本已移除，原始历史build目录及失败日志保留。`e8_scan_calibrated_13600ms.json`确认下载后在VISION_ONLY未ARM/零速明确恢复13600000μs/CALIBRATED_TIME，不能称运行时参数跨下载持久保存。

### E8首次真实蓝1落地接近停靠完成，末端微调仍慢

`build/remaining_20261104/integrated_blue1_e8_01.jsonl`结果为**DOCKED_OBSERVED**，116个CCTL快照、110个BCTL快照；110个B帧ID均不同、全部frameGood及目标locked。实体蓝1起始已完整入镜并锁定，模式INTEGRATED/REAL_CAMERA；执行一次主机START，合成写入和heartbeat均0，真实J3、IR及UART保护照常。没有把注入实验或像素仿真当作本次真实相机成功。

首次ARM记录为主机**2.169262秒**、APPROACH(+5,+5)、J3690mm。之后采样到J3462mm时降为(+3,+3)，J3365mm时出现(+4,+3)连续前进纠偏；约6.076秒到J3350mm但尚未居中，进入零速ACQUIRE，保留驻留与新fence后的三帧确认。随后约25.4秒为末端微调，轮询采到3次ALIGN(+3,−3)和多次ACQUIRE；短脉冲可能被轮询漏掉，不能把3个快照当成完整脉冲计数或实际轮速。

首次DOCKED记录为主机**31.484328秒**，距首次观察ARM **29.315066秒**：未ARM、左右0、zeroSent=true、J3 **329mm**有效，邻近独立B快照目标U110。之后12个DOCKED快照维持零速/未ARM，观察首末跨度**3.18423秒**，才由主机finally STOP并切VISION_ONLY；cleanupErrors为空，整个记录34.741535秒。C/B分别冻结，U与距离不能声称同一帧绑定；上述耗时是主机观察差，不是精确启动/机械停车或像素到UART延迟。

全程所见状态为IDLE/APPROACH/ACQUIRE/ALIGN/DOCKED，未见SEARCH、LOST、HOLD或IR触发。用户实物原话：“**持续向前，不明显偏转，左轮大概多走了1cm？探头前端距离大概33.5cm**”。这独立支持实际前进与停止位置；约1cm/33.5cm是用户估计，不能换算为已标定停车误差或轮端同步精度。板上329mm与用户约335mm分别记录，不把二者差值当作校准结论。

因此**蓝1已锁定起始的真实接近—减速—末端对准—DOCKED主功能本轮实现**，但约25秒末端微调、单次样本与估计的左右位移差仍是限制。蓝1阶段尚未覆盖其他牌、无目标起始搜索、实体POWER/红2、重复性和不同条件；后续蓝2分段记录见下文，不能倒填进本轮。生产源码冻结，不为单次成功删除E5/E7失败或E6时序失败。此蓝1范围已随提交`8626c39`发布，以下追加只更新现场证据，不更改既有R6/构建数值。

### E8蓝2分段记录：红2启动链成立，移动过程未被连续记录

**第一段为连续日志内的静止启动/近距完成。** `build/remaining_20261104/integrated_blue2_e8_red2_01.jsonl`包含99个CCTL、96个BCTL快照，主机START/合成写入/heartbeat均0，结果字段为DOCKED_OBSERVED，cleanupErrors为空。真实红2event7出现、当前选择蓝2的requestTag由8变9，重新锁定并ARM；ARM后采到5个ACQUIRE快照，然后DOCKED。关键边界是**全部99个C快照L/R均0、motionPermit均false**：前期J3约633mm，在出牌/摆位期间降至约295mm，启动后的292–303mm已在停靠距离内，无前进许可便进入终态。因此这段证明红2事件、新请求、锁定和ARM资格链，不是移动接近停靠。脚本的DOCKED_OBSERVED字段按原样保留，不将名称当成实物移动证据。

**第二段发生在该观察器结束以后。** 用户随后明确描述：最开始没有移动，按KEY0重置、把红2与红1重叠后车辆向前走，最终约40cm，可能受手/纸干扰。这是用户实际前进观察，但没有覆盖该过程的连续C/B/UART日志，不能补造起步时刻、所走距离、速度档位或红1/红2各自作用的唯一因果，也不能归入第一段99个零速快照。

`build/remaining_20261104/e8_blue2_after_operator_key0.json`提供事后终态佐证：初读C为INTEGRATED/蓝2/DOCKED、未ARM、L/R0、zeroSent=true、J3342mm有效、源健康且锁定，tag3；scanBudget=10000000、scanCalibrated=false，符合KEY0清除运行时标定。独立B读回仍E7070008、event7/id2、蓝2U141、框144×159（先前预检87×97），目标good/observed/locked。框变大与近处状态可以佐证场景变化，不能单独区分车辆移动与纸张移动；事后U141也不当作进入DOCKED瞬间的坐标。随后读取VISION_ONLY/IDLE未ARM/零速，`e8_scan_restored_after_blue2_key0.json`明确再次恢复13600000μs/CALIBRATED_TIME。

蓝2当前结论是**红2板上启动链已确认，用户前进观察加事后DOCKED佐证；完整移动遥测缺失、距离受干扰可能性保留**。不能写成与蓝1相同范围的全程停靠PASS，也不为补录日志重复本轮。E8源码、SOF、R6和构建结果均未改变；下一蓝3POWER试验的结果单独追加。

### E8蓝3：实体POWER启动的真实接近、差速减速与DOCKED

`build/remaining_20261104/integrated_blue3_e8_power_01.jsonl`为**DOCKED_OBSERVED**，257个CCTL、254个BCTL快照；主机START、合成写入、heartbeat均0，真实POWER启动资格链在本版获得实际运动任务证据。首次ARM在主机61.5772666秒，首次DOCKED77.3039882秒，差**15.7267216秒**；终态J3 **321mm**有效、未ARM、左右0、zeroSent=true。11个DOCKED快照首末跨度**3.127523秒**，之后STOP/VISION_ONLY零速收尾，cleanupErrors为空，完整含等待记录80.486497秒。时间仍为观察时间，不是机械响应延迟。

记录中12个非零APPROACH快照为(+5,+5)×2、(+3,+5)×4、(+3,+4)×6，真实距离从656mm经500mm降至334mm；约65.615秒进入ACQUIRE作末端微调，随后完成DOCKED，无SEARCH。这些计数是轮询到的命令状态，不当作UART报文数、轮速测量或每个原生帧的完整轨迹。

254个B快照全部good/fresh、无当前candidateOverflow/error，253次locked；唯一未锁定是初始新tag的ACQUIRING，不是运行中的坏帧。末B frame15822仍good/locked、U128、框152×169。清理后的C sourceHealthyFresh=false伴随mode切VISION_ONLY、新tag7→8请求重建，不能据此宣称末帧视觉失败或掩去正常的资格重建；最终未ARM/零速发送完成。

用户明确：“**稳定向前，最终距离大概31cm**”。本轮可计为**蓝3真实接近—差速减速—末端微调—停靠及E8实体POWER启动通过**，用户约310mm与J3321mm分开记录，不当成精密尺子校准。它补充蓝1主机START和蓝2红2分段证据，不追溯解释E7旧POWER无响应的唯一原因。蓝4等待摆位，蓝5/6及一次画外目标起始的真实搜索仍待；生产源码与既有构建/R6不变。

收尾边界另保留：在DOCKED零速保持期间，主机约80.119秒曾读到J3167mm、sonarHold=true，约80.431秒读到308mm、sonarHold=false；运动状态仍DOCKED、未ARM、左右0、zeroSent=true，没有复驶。不能写“全程无sonarHold”，也没有证据确认短近读数是尺量/手部遮挡造成。

### E8蓝4：真实接近停靠完成，保留起步抽动、偏右与慢微调

`build/remaining_20261104/integrated_blue4_e8_host_01.jsonl`为**DOCKED_OBSERVED**，99个CCTL、93个BCTL快照，一次主机START、合成写入/heartbeat均0。首次ARM主机2.1602634秒，ALIGN逻辑(−3,+3)、J3655mm；约7.300秒进入APPROACH(+5,+5)、642mm，8.043秒采到(+5,+3)、585mm，9.260秒采到(+4,+3)、487mm，11.206秒在334mm进入ACQUIRE零速微调。首次DOCKED在28.2996343秒，观察ARM至终态**26.1393709秒**，终态J3 **316mm**。

11个DOCKED快照首末**3.27686秒**均316mm、未ARM、左右0、zeroSent=true，之后VISION_ONLY零速清理，cleanupErrors为空；整段记录31.642262秒。93个B帧ID不同，全部good/fresh/observed/locked，无当前候选错误或overflow；框由84×94增至157×172，U从132曾降到77，最终111。未见HOLD/IR/LOST/SEARCH；轮询状态和请求cm/s不等于精确机械轨迹或实测轮速。

用户原话：“**启动的时候有抽动，然后偏右。直着向前接近后。停止，最后短向左修，修回居中（虽然还是有点偏右），最终停车距离大概32cm**”。本轮可以确认真实蓝4从对准、前进/差速减速、末端修正到停靠，但不能声称消除了偏航或起步不对称。用户约320mm与J3316mm独立保留；从约11.206秒停前进到DOCKED仍约**17.1秒**微调，速度慢及最终略偏右均为实际剩余缺陷。蓝5准备中，蓝6拟用唯一一次画外起始搜索，结果未预填；源码/构建/R6继续不变。

**随后用户缩减测试范围：**明确“**我觉得5/6都不用单独测了，1-4已经说明了性能**”。已取消上述蓝5/6计划，不再以它们作为本轮待执行或要求用户重复测试；最后一次画外搜索改用已摆好的蓝4，当前等待摆位确认。六牌静态识别证据仍成立，蓝5/6缺独立地面任务证据也仍成立，二者不混淆；搜索结果完成后即收尾发布，不追加逐牌扩测。

### E8最后蓝4画外搜索：曾发现目标，但停车后未锁定，最终NOT_FOUND

`build/remaining_20261104/integrated_blue4_e8_search_01.jsonl`保留完整记录：153个CCTL、150个BCTL快照，真实相机/实体POWER/真实J3与IR；主机START、合成写入、heartbeat均0。结果为**NOT_FOUND_OBSERVED / SCAN_BUDGET**，总观察49.482598秒，首次ARM22.954783秒，首次终态49.422059秒，两者差26.467304秒。累计许可SEARCH恰为13600000μs，不能把含停车/近障等待的26.467秒当成连续旋转时间。

| 主机观察时刻（秒） | 状态与实际读回 |
|---|---|
| 22.954783 | 首次ARM，SEARCH逻辑(+4,−4)，J3685mm有效 |
| 24.568753 | 进入ACQUIRE，C frame24263目标observed=true、locked=false，零速且zeroSent=true；累计扫描1.586529秒 |
| 26.999764 | 静止确认未锁定，恢复原方向SEARCH；未进入ALIGN或APPROACH |
| 31.709532 | J3240mm触发HOLD，逻辑零速，累计扫描6.286223秒 |
| 32.656468 | 距离2163mm，恢复SEARCH |
| 34.005920 | J3231mm再次HOLD，累计扫描7.475017秒 |
| 41.016427 | 用户移开障碍物后，读到4000/valid=true/FAR并恢复SEARCH；4000是远距哨兵，不是测得4米 |
| 46.869438 | 累计搜索到13.6秒，进入最后零速ACQUIRE |
| 49.422059 | 未取得目标锁定，NOT_FOUND/SCAN_BUDGET，未ARM、L/R0、zeroSent=true，J3297mm有效 |
| 49.482501 | finally STOP/VISION_ONLY/零速，cleanupErrors为空 |

用户报告扫过蓝4两次均未锁定，并询问是否扫速过快。首次ACQUIRE的CCTL确实有observed，而独立B轮询未必捕获同一原生帧；不以稀疏B快照否定C的发现。只读核对候选记录在停车后U约65→155→215→218，150个B读回均健康/新鲜，处理时间38.819–45.892ms，未见新增丢帧/候选溢出证据。这与停车后的目标继续越过视野相容，不能独立证明机械尾转时长或把失败唯一归咎于帧吞吐；中途近障和用户移障也是真实条件，未从日志中删掉。该轮没有ALIGN/APPROACH/DOCKED，不能算画外搜索停靠通过。

### E9：用户追加看到目标后有限回扫，源码实现及聚焦回归

用户随后明确：“**如果是看到后，停转但是过了，我觉得可以加一个停转后慢速或小步回扫的功能**”。因此采用只在曾见目标后尝试有限反向小步的修正；没有把全部SEARCH改成周期步进，也没有降低到尚未证实能可靠起转的速度。E9设计ID由顶层标记为`E7070009`，控制修改为`motion_fsm.sv`和`member_c_control.sv`，专项回归为`tests/member_c/tb_control_repair.sv`。

- **授权只来自正向SEARCH本次目标的发现。** 该发现使车辆进入原ACQUIRE；完整零速UART完成、保守驻留1.5秒、新采集fence之后等待三帧锁定。只有确认超时、来源仍健康、当前已无targetObserved且仍有扫描预算，才允许反向；启动时已见目标、普通ALIGN/APPROACH/LOST/HOLD的确认超时不会自行授予回扫。
- **每步最多150000μs、全任务最多3步。** 参数为`BACKTRACK_PULSE_US=150000`及`BACKTRACK_MAX_STEPS=3`；复用SEARCH状态，另存本步方向。生产正常SEARCH(+4,−4)，回扫(−4,+4)cm/s；方向固定为原搜索方向的相反，不按最后U重新选向，也不前进追赶。零参数禁用；允许步数1–3、脉宽1–200000μs，超范围禁用，2bit步数不会环绕。
- **反向也计入同一累计预算。** 仍由SEARCH下实际许可的逻辑运动累计scanElapsedUs，剩余不足150ms时预算先行撤销输出；不重置13.6秒预算，也不重新给一圈。每步开始即消耗一次尝试，HOLD或源失效不退款；在同一任务后来再见目标也不能取得第4步。原120秒任务总限仍连续计时。
- **每一步后完整停车重确认。** 到时、再次observed或预算用尽立即撤销组合轮速请求，进入完整ACQUIRE。成功新锁定后才走原ALIGN；仍失败且有资格/余量时执行下一步，否则恢复原方向的剩余SEARCH。反扫中发生源失效或HOLD，回扫授权立即撤销，并保留“尚需停车确认”标志；恢复健康/安全后任何正向运动前仍必须零速UART、完整驻留、新fence与确认等待，不能因转入HOLD/LOST绕过它。
- **取消不复活。** STOP、IR、选择改变、模式切换、raw模式、注入租约失效、reset清除旧回扫资格/步数/待确认标志，新任务才获得新计数。成功锁定清除回扫资格但不返还本任务已用次数。原J3/IR、健康门控、APPROACH差速、ALIGN脉冲与三帧资格保持。

150ms表示逻辑请求允许窗口，不是已测轮端转动时间或角度；1.5秒也仍非已证明的机械停稳上界。反向使用原4cm/s可避免引入更低档，但反复启动仍可能受已见起步不对称影响。13.6秒现在同时包含正反转，不能再把该任务预算等同于保证正向扫过完整一圈。回扫能否在本车收回目标仍须本版实机确认。

**聚焦ModelSim结果：**`build/remaining_20261104/control_e9_20261104T171519Z/result.json`为PASS，两种TURN_SIGN各**696检查、245条完整UART**；每种spin111/drive30/zero104，转向细分low41/high62/fineLow6/fineHigh2，原差速JSON检查全部保留。编译加负/正两次仿真实际执行合计**20.8500433秒**，0 errors/0 warnings；不跨符号累加为1392个独立需求。覆盖真实完整反向UART、150ms到限、三步与第四拒绝、剩余预算截断、总任务计时不重置、新fence后三帧重获、源/HOLD中断后的完整等待及七类取消不自启。测试将驻留/确认超时缩短以验证时序关系，但保留150ms回扫参数；仿真不作为车体停稳验证。

首次宿主包装器错误匹配`PASS `而未包含日志实际的`PASS:`，把已经通过的负sign仿真误记FAIL；原记录保留`wrapper_result_initial.json`。**负sign仿真本身一次PASS，未重跑**；仅用同一编译库执行尚未运行的正sign，然后按真实日志纠正`result.json`。`commands.json`、`negative.log`、`positive.log`保存命令与原输出，不能把宿主误判写成修复过RTL功能失败。独立只读审查通过；原14帧真实像素回归输入/断言不变，随后在本版正式R6中实际通过。

20.8500433秒为编译与负、正仿真调用的累计执行时间，不含修正包装器匹配规则的间隔。TB保留150000逻辑微秒门限，但共享timeUs每20 ns时钟递增1，UART与驻留均加速；不把该验证解释为板级150 ms管脚脉宽或机械停稳测量。

| E9发布步骤 | 当前事实 |
|---|---|
| 生产源码与专项TB | 已冻结；聚焦两sign PASS如上 |
| 正式R6 | **PASS，274.530007秒 < 285秒目标**，13 PASS + CAUGHT、cleanBuild=true、targetMet=true、退出0，Verilator5.050、jobs4；`build/member_b/20261104T171630_007376Z_verilator_course/result.json`。原14帧像素及本版696检查/245UART控制回归实际通过，不复用E8结果 |
| Full Compilation及post-fit | **PASS，1218.109秒＋26.779秒**，`build/member_b/20261104T171519_480274Z_build/`；ALM29699/32070（93%）、setup/hold +0.629/+0.117ns，未约束项0 |
| E9下载及身份读回 | **PASS**，原始SOF6706161字节，`program_e9_console.log`中buildIdVerified=true；UTC17:36:35.545149完成 |
| E9实际回扫/画外搜索停靠 | **INCOMPLETE**；实体POWER起动，搜索发现/锁定后持续对准，60秒观察窗无DOCK，主机STOP/VISION_ONLY零速收尾，无cleanup错误；反向SEARCH未触发，回扫物理效果未验证 |

不继承E8的构建或实物通过；蓝5/6独立地面测试取消的用户范围保持，后续仅围绕本次新增回扫补必要验证。

### E9 Full Compilation、下载与本轮零速预检

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

### E11：停车状态下的小范围调参

本节记录E11首次引入的通用接口。E14新增policy可调正常停车/减速距离及驻留，生产启动值也已变化，以上方E14表为准。

此节对应已下载的E11；旧版E10没有调参能力，配套新工具读取旧板时会拒绝写入，不会把旧状态字当作新调参寄存器。`tune`无参数只读状态，查看`tuningSupported`与`tuning`；指定任意字段时，先读当前五项、合并本次修改，再一次原子写入整组并读回核对。所有值必须是表内整数，且`approach > fine`。这些是控制器的逻辑cm/s请求与像素容差，不是电机PWM、实测轮速或遥控车轮接口。

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

## 2026-11-05：E12发布——ALIGN分段短转与独立实机记录（E7070012）

用户要求继续现有主线，并增加短转起步参数。E11两次画外搜索NOT_FOUND、三个短时对照INCOMPLETE的事实保留；E12不将这些缺陷改写为已解决。源码冻结后，本版独立控制、R6、完整构建/post-fit、下载及静止pulse均已通过，具体结果如下。本次发布E12，板上已核对该身份；五轮实机记录如下，主线停靠仍未通过。

新增独立opcode12及STATUS word15 A2能力，原opcode11/word13 A1不变。四项为minMs/maxMs各20–300（10 ms步长且min≤max）、kickMs0–100（10 ms）、kickSpeed3–8 cm/s；默认20/100/0/5，kick关闭，保持E11默认短转。min仅限制计算的名义总时长，丢牌/跨方向/居中或IR/J3可提前停车，实际可能短于min；kickSpeed为UGV02 UART速度请求，不是PWM/电流/转矩或实测轮速。总时长按误差×2 ms夹在min/max内且**包含起步段**，kick截断至总时长，剩余沿原方向用既有turn或小误差固定3。只作用ALIGN，SEARCH和APPROACH不加kick；原stop/居中/跨方向/保护中断及驻留恢复保持。

CLI `pulse`无选项只读；`--min-ms/--max-ms/--kick-ms/--kick-speed`合并原四项后整组原子写入并独立读回，`--defaults`独占恢复四项默认。VISION_ONLY、未ARM、无permit、LR0、zeroSent是主机与RTL双重写入条件；无自动切模式/START/heartbeat。pulse与tune独立、pulse不清扫描标定、改变search仍清标定；KEY0/掉电/下载恢复volatile默认。旧E11无A2拒绝pulse写，保持原tune可用。详细范围、CLI示例与协议字段见中英README新增E12节。

协议定向`build/remaining_20261104/pulse_e12_20261104T192735Z/result.json`：HDL **193检查/20报告、1.5672301秒PASS**；Python **24项、0.141秒PASS**；生产Tcl脚本与模拟transport **2项、1.037秒PASS**。这些不是实板调参或机械起转证据。控制定向已有下述独立PASS；正式R6已有下述独立PASS；完整编译/post-fit及实际下载/静止pulse已有下述独立结果；E12五轮实机结论见下文；只有第四轮有限回正被用户接受，其余未完成，不称机械同步或过冲已解决。


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

发布记录以这五轮为界。随后只有**tolerance40→30**改变，形成**tune3/3/5/4/30、pulse200/200/60/6**的同版本独立诊断，扫描仍15.1秒；原五轮发布快照将该诊断标为待验证；现在第六轮独立结果见下文，连续差速修正已获用户确认，但不据此声称完整停靠通过或通用推荐设置。该调参不新增RTL、编译或固件版本。SOF的复位默认仍是**tune4/4/5/3/30、pulse20/100/0/5**；KEY0、掉电或重新下载不会保留实验配置与扫描标定。原E8已见目标停靠及所有历史失败继续按各自版本保留，不能覆盖本轮未完成的主线功能。

### E12第六轮tolerance30：连续差速接近已观察，按诊断规则提前停车

本轮仍为**E7070012**，没有RTL变化、重新编译或新增R6；仅沿用停车时的**tune3/3/5/4/30、pulse200/200/60/6、扫描15.1秒**。`build/remaining_20261104/integrated_blue4_e12_tolerance30_approach15s.jsonl`保留**316C/28B**，taskObservationSeconds **2.2937077秒**，结果**APPROACH_INTERRUPTED**。本次诊断规则是在首次离开APPROACH时立即由主机STOP；因此该结果不是观察了自动恢复后宣告失败，也不是60 cm到DOCK的完整任务验收。

任务中连续采到**10个5/4、11个5/5、4个4/4**轮速请求状态样本，U由**77→87→113**。这些数字是重复状态快照数量，不是独立UART命令包数或实测轮速。用户确认：“**确实是不断修正，虽然最后有点偏右，但在可接受范围**”。结合其物理观察，本轮已经取得连续前进与差速修正的实机证据，区别于前五轮以反复原地对准为主的现象；但不据一次不同起始摆位的诊断认定容差是全部问题的唯一原因。

J3读数由约**625 mm下降到首次LOST时约440 mm**，清理后约**426 mm**。本轮没有ALIGN或SEARCH，最后已采B框完整；**恰好失锁对应的B帧未采到**，不能用最后完整框证明失锁帧也完整，亦不能将原因直接归为边缘裁切或传输故障。主机在此处终止，未继续观察E12的LOST→ACQUIRE恢复或后续DOCK过程。

随后独立`e12_after_tolerance30_preflight.json`的**3个样本均健康锁定，U141，J3分别414/414/409 mm**，保持VISION_ONLY、未ARM、零速。其位置与本轮末U113是不同采集时点，不能合并为同一帧或无变化的连续轨迹。后续从约41 cm位置的独立任务已取得DOCKED，详见第七轮；其两种距离读数差异仍保留。本轮与后续近距段即使都成功，也须保持分段证据，不能拼接成单次从60 cm自主到DOCK或从画外搜索到停靠的完整通过。

### E12第七轮独立近距任务：板上DOCKED，尺量与J3差异保留

`build/remaining_20261104/integrated_blue4_e12_tolerance30_final_approach.jsonl`从约41 cm位置**重新按实体POWER**开始独立任务，仍用**tune3/3/5/4/30、pulse200/200/60/6、15.1秒扫描预算**。记录**385C/52B**，host START、synthetic写入、heartbeat均0；结果**DOCKED_OBSERVED**，taskObservationSeconds **14.885635秒**，cleanupErrors为空。没有新RTL、SOF、构建或R6。

首见ARM在观察器时间**40.6648686秒**，APPROACH4/4、J3 **416 mm**；首见DOCK在**52.4846055秒**，J3 **292 mm**，即首见ARM至DOCK约**11.8197369秒**。随后**22个DOCKED快照跨3.065829秒**，均未ARM、无permit、左右0、zeroSent=true、健康锁定，J3均292 mm。该段证明板上自主进入DOCK并保持零速状态，而不是主机先STOP后补记DOCK；zeroSent和状态驻留仍不等于独立测得机械停车延迟。

过程先4/4（D416），再近距右纠偏4/5（D381）并于D339进入ACQUIRE；随后多次反向ALIGN/ACQUIRE，B位置约U163/164→162→161→158→152→140/141，最后回到90–150居中带。**没有LOST或SEARCH样本**，因此本轮不能作为失锁恢复或搜索功能验收。全部ARM期间来源健康、测距有效，没有HOLD/IR/fatal，scanElapsed为0；52个B样本未见候选或传输故障。最终横向框U58–225完整，但纵向触V319下边缘，不能描述成四边都留有余量。C/B独立冻结，也不把邻近采样当成同一帧轨迹。

| 停车距离来源 | 本轮结果 | 含义 |
|---|---:|---|
| J3板上读数 | 292 mm（29.2 cm） | 首DOCK及22个DOCKED快照一致 |
| 用户按“探头前端到纸板”尺量 | 约37 cm（370 mm） | 用户本轮实体测量反馈，未改成35 cm |

两者相差约**78 mm**，原因尚未确定；不平均、不选择其中一个覆盖另一个，也不据此宣称精确35 cm停靠或已完成超声绝对精度标定。该轮实际范围是**约41 cm重新启动后的已见目标停靠**，不能与第六轮被主机中断的625→440 mm段拼成一次60 cm到DOCK的连续自主任务。随后第八轮画外搜索的独立INCOMPLETE结果见下文；本轮成功不覆盖前五轮失败、取消的蓝5/6地面测试或尚未完成的画外搜索停靠。

### E12第八轮画外搜索：找到并恢复目标，但反复对准未停靠

`build/remaining_20261104/integrated_blue4_e12_tolerance30_search_to_dock.jsonl`使用**tune3/3/5/4/30、pulse200/200/60/6、15.1秒扫描预算**，记录**671C/84B**；host START、synthetic写入和heartbeat均0。taskObservationSeconds **60.1513566秒**，结果**INCOMPLETE**，原因为“60 s task observation limit reached during vision read”。这是60秒主机观察窗在读B期间到限，不是120秒产品任务时限耗尽，也不是DOCK。cleanupErrors为空；最终VISION_ONLY、未ARM、permit0、左右0、zeroSent=true、J3 **390 mm**，IR0、sonarHold0。

初始SEARCH以`+3/−3`请求累计**2.553478秒**即找到蓝4，剩余扫描预算**12.546522秒**。此后**没有新增SEARCH，也没有reverse SEARCH**。采样保留7段APPROACH、18段ALIGN和6段LOST；六段LOST均经ACQUIRE后恢复，并未再次重转圈。这是扫描预算未耗尽情况下恢复路径的实板证据，不是稳定机械跟踪或完整停靠成功；分段数量来自离散状态快照，不等于所有原生状态切换数或转向脉冲数。

B坐标曾约U195停留10秒、U65停留5秒，末段U124→176→171仍越出跟踪纠偏上界165。用户实际反馈：找到B4后牌滑到VGA右边缘，随后转动伴随前移、牌跨到左边缘，慢慢回正后仍在右边缘留小缝。该反复越过目标的现象保留，不能以输入/恢复路径正常宣称过冲已解决。J3由约628到390 mm仅是探头方向测距变化，**不能称车辆真实前移238 mm**。

用户补充**相机到标牌约47 cm**，而板上最终**J3为390 mm**。测量原点/方向不同，不能直接当同基准测距误差、用于超声偏置标定或取平均。第七轮292/370 mm是两项均明确以探头前端为基准的读数，其差异仍未解决；不可混为这一轮47 cm相机距离。

| 第六至八轮后续实机 | 已观察结果 | 证据边界 |
|---|---|---|
| 第六轮tol30接近诊断 | 用户确认连续差速修正，5/4→5/5→4/4请求 | 首LOST即hostSTOP；未观察后续恢复/DOCK，失锁B帧缺测 |
| 第七轮独立约41 cm任务 | DOCKED_OBSERVED，22个零速样本跨3.065829秒 | J3292 mm/探头前端尺量约370 mm差异未定；不拼接第六轮 |
| 第八轮画外搜索 | 2.553478秒搜索即发现，6段LOST均经ACQUIRE恢复，无再次SEARCH | 60.1513566秒INCOMPLETE，反复ALIGN、边缘来回、未DOCK；相机47 cm与J3390 mm基准不同 |

这批记录在第八轮后独立提交，保留原五轮失败和有限诊断。随后仅**turn3→4**，形成**tune3/4/5/4/30、pulse200/200/60/6、扫描15.1秒**的最多15秒第九轮隔离，此前快照将第九轮标待验；现有限诊断结果见下文，不是完整任务通过。只调整既有粗ALIGN后段请求，小误差固定3的规则不变；正在试的组合不算已验证、推荐或主线完成。原SOF与产品PDF不因此更换或重编译，历史R6没有新增执行。

### E12第九轮turn4隔离：方向改善获反馈，进入接近通道即停车

在相同E7070012中只改**turn3→4**，配置为**tune3/4/5/4/30、pulse200/200/60/6、扫描15.1秒**，没有RTL、SOF或构建变化。`build/remaining_20261104/integrated_blue4_e12_turn4_reverse_align15s.jsonl`结果**ALIGN_CORRIDOR_OBSERVED**，taskObservationSeconds **1.7750441秒**，共**1228C/111B**；绝大部分快照用于等待实体POWER，首见ARM在观察器时间**115.1999995秒**，不能把等待时间或总快照数写成持续运动时长/采样率。

直接采到`ALIGN −4/+4 → ACQUIRE 0/0 → APPROACH 4/5`，首次APPROACH触发诊断主机STOP。起步kick6未被这次稀疏轮询采到，不能由配置值补造完整6→4实板命令序。B为U171→164，末VISION_ONLY、未ARM、左右0、zeroSent=true、J3约388 mm，cleanupErrors为空，**没有DOCKED**。用户原话：“**更稳定，并且能向中间移动，但没能居中**”。该观察支持本轮有可接受的方向改善，不能升级为精确居中、持续闭环或通用推荐。

之后独立静止`e12_after_turn4_alignment_preflight.json`取得**3/3健康锁定U147，J3分别379/379/383 mm**，该预检位置位于允许居中带90–150。它与任务中的U164是不同采集时点，不能组合成已测机械停稳曲线、精确停止延迟或同帧前后关系。随后同一参数的第十轮完整画外搜索仍INCOMPLETE，详见下文；本轮有限诊断不替代该任务。

### E12第十轮完整搜索仍未完成：逻辑5/5不等于物理直行

`build/remaining_20261104/integrated_blue4_e12_turn4_search_to_dock.jsonl`使用**tune3/4/5/4/30、pulse200/200/60/6、扫描15.1秒**，记录**613C/79B**，host START、synthetic写入和heartbeat均0。首见ARM在观察器时间**24.2043404秒**、SEARCH状态、J3约699 mm。taskObservationSeconds **60.0024068秒**，结果**INCOMPLETE**；主机60秒观察限到期，不是产品120秒任务时限或正常DOCK。cleanupErrors为空，最终VISION_ONLY、未ARM、左右0、zeroSent=true、J3约**524 mm**，IR0、sonarHold0。

用户原话：“**一直左右调，哪怕居中后还继续调到另一边边缘，并不会往前直走**”。机器多次采到APPROACH5/5，但邻近B坐标出现U141→201、U119→76、U114→196、U143→60的明显跨画面变化。离散C/B快照不是同一原生帧，不能据此精确重建每次物理偏转时刻；不过该命令与实物反馈的不一致必须保留。**相等的左右逻辑请求不证明两轮实际速度相等、车身直行或转向后的机械运动已停止**，不把“读到5/5”写成前进效果通过。

第九轮短诊断“更稳定”的用户反馈不被删去，但其有限观察也不覆盖第十轮长任务中的反复横向调整。当前组合仍属于实验记录，不推广为推荐参数；没有DOCK或完整搜索停靠通过。后续暂不继续长时间实车试跑，转为只读核查ALIGN到前进的命令顺序及起步不均，尚不把软件转序、底盘响应、供电或机械差异中的任何一个写成已确定根因。此轮没有修改RTL、SOF、产品PDF或重新执行R6。

### 第十轮补充：单侧实际运动与底盘固件语义未核实

用户进一步确认：**“请求了，但实际几乎只动了一边”**。因此本轮缺陷不仅是泛称“不直走”，还包括相等逻辑请求下明显不对称的实物响应；当前没有独立轮速反馈证明左右匹配。

截至2026-11-05核查，官方[General_Driver速度入口](https://github.com/waveshareteam/ugv_base_general/blob/main/General_Driver/movtion_module.h#L275-L303)仅mainType3启用PID，其余含UGV02/mainType2将输入乘512及左右倍率后交给PWM；官方[ROS_Driver速度入口](https://github.com/waveshareteam/ugv_base_ros/blob/main/ROS_Driver/movtion_module.h#L246-L268)则启用PID。这说明官方源码存在不同控制路径，不能只凭接口单位标签认定现场固件行为。

本文和日志的**cm/s是FPGA名义请求单位**，后续OLED已确认UGV Rover/version0.9，但已安装镜像与源码的对应、具体运行语义和实际轮速仍待核实；见后续零速流量记录。本记录不据现象直接断言PI积分问题、电机损坏或某个软件根因，也没有修改或刷写底盘固件。既有实物现象与各轮结果保留，后续核查另列。

### 第十轮只读协议审计：健康输入及停车到前进边界

独立审计得到**447个ARM期间C样本**，全部sourceHealthyFresh、distanceValid、selectionMatches=true；IR/HOLD/fatal/RX framing error均false。79个B样本全good/fresh，无candidate overflow/error/overrun或transportFaultSticky；completionDiscard=0，bufferDrop始终为历史值2、没有新增丢弃。处理时间39.309–50.810 ms、快照采集年龄41.410–88.097 ms只对应这些采样，不是图像变化到轮子响应延迟。

可见状态分段为SEARCH2、ALIGN21、APPROACH4、LOST9、ACQUIRE27；都是离散采样分段数，不是精确全状态次数。累计SEARCH **5.155026秒**，余**9.944974秒**，所有已采SEARCH均+3/−3，没有反向SEARCH或DOCK。最终B为U60、横向框U11–109，J3最终524 mm。

七组同段ALIGN直接采到kick6→cruise4（反向5组、正向2组），之后有零请求；这是板上状态/命令证据，**没有实机TX逐位解码，也不能推出精确脉宽或实际轮速**。四个APPROACH入口都为5/5，各入口之前最近C样本均是ACQUIRE、左右0、zeroSent=true、uartBusy=false。总共14个APPROACH样本中11个5/5，另有4/5两次、5/4一次；它支持发送侧已呈现停车完成到前进的边界，仍不证明机械已停稳或两轮同步起步。

此次只读审计没有找到能由已采证据证明的命令发送侧bug；这不是对所有未采时序的排除，也不等于完整控制策略无问题。结合用户“几乎只动一边”的反馈，下一步需先核对已安装底盘固件语义与实际响应，保持根因未定，不继续把逻辑速度请求直接当作实测车轮速度。

第十轮后首次OLED读取只见`AP:UGV`、`ST:OFF`和**11.27 V**，当时没有启动车型/Version；MAC不写入记录。单个电压读数不构成低电故障结论。后续只准备核对启动信息；截至本快照没有底盘flash、PID/PWM或车型配置写入。

两个只读代码审查分别核对：居中退出ALIGN后先zeroSent、1.5秒驻留、新fence三帧再进入APPROACH；同向5/5左右分别编码，没有发现单侧符号翻转；`chassis_command`没有非零指令FIFO，发送一份完整包、STOP优先。28字节在115200 baud的串行时间约2.43 ms，已检查的这一层不支持秒级指令排队解释。既有UART管脚级仿真覆盖相关逻辑，本次未重跑或新增测试，也没有底盘实际ACK/轮速证明。结论仍是**未发现确定的FPGA控制/发包bug，底盘模式及响应待核实**，不是彻底排除FPGA。

### E12后续非运动核查：OLED版本确认及自动反馈停止

用户实际读到开机OLED **UGV Rover / version0.9**。此前OLED电压11.27 V，页面后来给出的原对象为`{"T":1001,"L":0,"R":0,"r":-1.184410511,"p":0.192824244,"v":11.17282963}`。这是用户看到的页面数据，**不是T131专属ACK，也不是主机采集的实时轮速记录**；L/R为0不代表已经验证运动中的轮速闭环，单个电压读数也不构成低电故障结论。显示版本已确认，但没有读取现场固件二进制并证明其与某个源码提交完全一致。

用户重启底盘后，重新下载了原有**E7070012同一SOF**，随后恢复VISION_ONLY、**tune3/4/5/4/30、pulse200/200/60/6、scan15.1秒**。证据为`program_e12_after_ugv_version_check_console.log`及`e12_after_ugv_restart_*_console.log`；没有新的RTL、SOF编译或R6，也没有刷写ESP底盘固件、修改PID或车型设置。

| 独立零速RX观察 | FPGA时间timeUs | chassisRxCount | 结果 |
|---|---|---|---|
| `e12_ugv090_rx_preflight.json`样本1 | 233294191 | 1523 | V1、未ARM、左右0、zeroSent |
| 同文件样本2 | 233631613 | 5232 | 相邻337422 µs新增3709字节，约10992.2 B/s |
| 同文件样本3 | 233980951 | 9079 | 相邻349338 µs新增3847字节，约11012.3 B/s |
| `e12_ugv090_rx_after_flowoff.json`共5样本 | 641121327→642654185 | 五次均1230 | 独立窗口约1.533秒内0新增字节，全程V1、未ARM、左右0、zeroSent |

两个文件之间计数器曾回绕，**不跨文件相减，也不把9079→1230当作流量或丢失数**。在两个窗口之间，用户通过手机发送`GET /js?json={"T":131,"cmd":0}`，只关闭本次底盘RAM中的自动反馈；随后独立RX窗口不再增加提供了效果证据，而不是依赖网页ACK。FPGA自身feedback原本为0，主机没有发T130主动查询。以上是零速接收流量核查，不能由flowoff推断单侧运动、过冲或停靠问题已解决。

官方0.90的[串口解析serialCtrl](https://github.com/waveshareteam/ugv_base_ros/blob/53c25eb5007e73779ad54526c89bb1b738f1dd1d/ROS_Driver/uart_ctrl.h#L503)支持连续换行JSON；[T131路由](https://github.com/waveshareteam/ugv_base_ros/blob/53c25eb5007e73779ad54526c89bb1b738f1dd1d/ROS_Driver/uart_ctrl.h#L66)及[反馈模式函数](https://github.com/waveshareteam/ugv_base_ros/blob/53c25eb5007e73779ad54526c89bb1b738f1dd1d/ROS_Driver/ugv_advance.h#L365)只改变反馈开关，默认配置为开启。参考[PID_v2采样门控](https://github.com/imax9000/Arduino-PID-Library/blob/master/PID_v2.cpp#L26)：默认100 ms，因此60 ms kick在某些相位关系下可能在计算前被后续设定覆盖；这只是**机制推断，尚非本车现场因果证据**，更不能直接断言积分故障。

下一步拟在同一版本、真实J3/IR安全链下进行最多4秒、固定坐标三阶段的连续改值检查；该检查后续已执行trial1，因真实500 mm距离规则提前结束，详细记录如下，不写完整运动PASS。零速流量结果和后续物理运动结果将独立记录。

### 关闭反馈后的连续改值trial1：前两段请求已保持，第三段被距离规则终止

本次是独立**CHASSIS_INJECT**隔离检查：固定合成视觉坐标进入真实C控制器/FSM，再经真实安全保护和UART输出；**没有直接写左右轮速或伪造超声距离**，不是相机标牌闭环任务。`e12_continuous_command_preflight.json`两个独立样本均为真实J3 **717 mm**、VISION_ONLY、未ARM、zeroSent=true、RX1230。自动反馈已关闭，本轮RX计数也维持1230。

`build/remaining_20261104/e12_continuous_command_flowoff_trial1.jsonl`记录**46个C样本、一次host START**。在同一活动任务中，阶段1合成U120对应**5/5**请求，已采保持**1.0229965秒**；阶段2合成U80对应**5/4**请求，已采保持**1.0288990秒**。这些是状态中的逻辑请求保持时长，不能直接当作两轮实际速度持续时间。第三段恢复同速没有完整完成；独立协议核查确认第三段4次5/5快照跨约198.598 ms，但不足完整1秒，不补造完整三段通过。

结果为**INCOMPLETE**，原因为`ProbeStopped: real measured J3 clearance must be >500 mm`；真实测距达到**500 mm**时触发诊断专用距离规则，主动结束。它不是J3近障HOLD、IR急停或主任务停靠失败。cleanupErrors为空；最终VISION_ONLY、未ARM、permit0、左右0、zeroSent=true、J3 **500 mm**、IR0、sonarHold0、RX1230。717→500 mm只是测距变化，不能写成精准移动217 mm或据此反算实际车速。

helper的预算从START请求开始最多4秒，预留最后0.5秒发送STOP；阻塞中的JTAG调用及清理可能跨过主机时间边界，因此不等于已量得机械4秒硬停止。此helper和7项fake传输检查仅为ignored `build/`中的实验工具，不属于新增生产RTL验证；本版源码、SOF和R6均未变。trial1用户未仔细观察、没有物理验收；关闭反馈是否改善运动未获结论，不宣称运动问题已修好。

### 关闭反馈后的连续改值trial2：三段请求完整观察与有限物理确认

trial1用户明确表示没有仔细看，因此**没有获得物理验收**，并要求复演。协议复核在trial1第三段读到**4个5/5快照、首末约198.598 ms**，但没有完成该段完整1秒；原INCOMPLETE及距离诊断停止结果保留，不能补成三段通过。

复演记录`build/remaining_20261104/e12_continuous_command_flowoff_trial2.jsonl`仍使用合成视觉→真实C/FSM→真实J3/IR保护→UART，**只发一次host START**。结果为**THREE_PHASE_REQUESTS_OBSERVED**，共**60个C快照**；同一活动任务内三段完成如下：

| 阶段 | 合成U | 板上逻辑请求 | 已观察保持时长 |
|---|---:|---|---:|
| 1 | 120 | 5/5 | 1.040495秒 |
| 2 | 80 | 5/4 | 1.0156123秒 |
| 3 | 120 | 5/5 | 1.0268218秒 |

最终VISION_ONLY、未ARM、permit0、左右0、zeroSent=true、J3 **855 mm**、RX **1230**、IR0、sonarHold0，cleanupErrors为空。自动反馈持续关闭；没有用直接轮速命令绕过C控制链，也没有注入假距离。三段状态请求完整观察只证明本轮名义请求转换，不等于实际轮速、位移、转弯幅度或用户已经看清；**trial2用户已确认较快→较慢→较快→停车**，更精确范围见后续独立审计。这不是相机目标跟踪、停靠或关闭反馈导致运动问题修复的独立证明。源码/固件/编译/R6未新增，本次物理反馈和独立审计已补齐，按这一有限范围发布记录。

### trial2物理反馈与独立审计：连续三段变速和停车已观察

用户反馈：**机器人较快行驶一段→较慢行驶一段→恢复此前较快行驶→目前已停**。因此可以确认本次连续请求变化确实反映为可见的三段运动变化及停车；用户没有分别确认两轮一直转动、微转方向或精确速度，不能把该反馈升级为左右5/4差速量值验收。没有同条件flow-on对照，也不能认定关闭自动反馈已经修复原来的单侧运动/对准问题。

独立审计确认trial2的60C中**54个ARM样本均处于APPROACH**，请求顺序只有5/5→5/4→5/5，三段保持1.040495/1.0156123/1.0268218秒。ARM期间来源健康、目标锁定、租约有效，IR/HOLD/fatal均0；**全部60个C样本RX恒1230**。START请求至STOP请求**3.4557113秒**，最终零速确认约**3.5274695秒**，在本次4秒主机预算内；这不是实际机械制动时间的独立测量。cleanupErrors为空，最终V1未ARM、左右0、zeroSent、J3约855 mm。

两次模板commit ACK到首次读到新请求分别约**132.4/141.3 ms**，包含主机轮询和合成报告成帧/确认，不是底盘接收或机械响应延迟。复演前独立`e12_continuous_command_replay_preflight.json`两组蓝4健康锁定U84、真实J3 **1249 mm**；这个预检与trial1的717 mm不是同一摆位，任何测距变化均不用于反算精确实车位移/速度。

本次记录到此可确认**连续改值+三段变速+停车在该隔离检查中已观察**，仍非相机跟踪停靠或完整主流程通过。trial1“没仔细看”及其未满第三段的结果保留。下一步只准备单次ALIGN→zero/驻留→APPROACH的最小过渡诊断，尚无结果，不继续60秒长任务；仍使用E7070012，不新增版本、RTL编译或生产R6。实验helper及fake检查仍留在ignored build中。

### E12单次转向到前进：完整零速驻留后恢复，两轮参与运动获确认

`build/remaining_20261104/e12_single_turn_to_forward_flowoff_trial1.jsonl`是与真实相机搜索分开的CHASSIS_INJECT隔离检查。固定合成目标只经真实C/FSM、真实J3/IR安全链和UART作用于底盘，没有直接写轮速或伪造距离。沿用E12、tune3/4/5/4/30、pulse200/200/60/6及15.1秒扫描基准，底盘RAM自动反馈仍关闭。本轮一条host START，有合成目标更新及租约保持；不能套用真实相机任务的“无注入/无heartbeat”表述。

独立协议审计确认结果为 **SINGLE_ALIGN_ZERO_FORWARD_REQUESTS_OBSERVED**，共 **60 C、54 ARM样本**，只观察到一次ALIGN，随后ACQUIRE和APPROACH，没有第二次ALIGN、SEARCH或LOST采样：

| 阶段 | 直接观察到的请求与状态 | 证据边界 |
|---|---|---|
| 一次ALIGN | 2个6/−6，再2个4/−4样本 | 符合两阶段请求；不是实测轮速或引脚TX逐位解码 |
| 停车重确认 | 31个ACQUIRE样本均左右0、zeroSent=true、UART idle | 本地零速报文完成；不等于机械停稳时间已测 |
| 前进 | 19个APPROACH样本均5/5，首末跨度0.920350秒 | 请求状态被采到，不等于精确1秒物理直行 |

START后 **0.267321秒**已自然进入ACQUIRE并完成零包；**0.311450秒**才首次发TX5把合成U改到120，**0.343871秒**取得commit ACK，因此没有靠提前改U截断转向。零确认到首个APPROACH为 **1.611663秒**。ACQUIRE中的帧208/209健康且observed、锁定位清；帧211恢复锁定并进入APPROACH，与生产驻留后的新三帧重确认一致，但没有直接采到单周期fence。计划前进截止时正在进行的C读取越过截止约34.774 ms，不能称精确物理脉宽。START请求到STOP请求 **2.799345秒**，最终零速确认约 **2.842336秒**，在本轮6秒主机预算内。

ARM期间来源与租约、有效非FAR距离和实体选择健康，IR/HOLD/fatal/framing-error均0；ACQUIRE正常重确认中的短暂锁定位清不当作运动失锁故障。60个C样本RX恒1230。cleanupErrors为空，最终VISION_ONLY、ARM0、permit0、左右0、zeroSent=true、UART idle，J3 **730 mm**。

用户实际反馈是 **“两侧轮子都一起走的”**。这支持本次检查中两轮参与运动、没有报告仅单侧动作；用户没有逐段确认旋向、直行精度或精确时长，不能补写这些结论。没有同条件flow-on对照，仍不能确认关闭遥测是原问题的因果修复。它也不替代真实视觉发现目标、持续跟踪和停靠验收。

### E12关闭反馈后的真实相机搜索：60秒仍未停靠

随后独立真实相机任务记录在 `build/remaining_20261104/integrated_blue4_e12_flowoff_search_to_dock.jsonl`。E12源码、SOF及上述运行参数未改变。本轮 **729 C / 90 B**，任务观察 **60.0067485秒**，结果 **INCOMPLETE**；未读到DOCKED或其他终态，观察窗结束后由主机STOP收尾。host START、合成写入和heartbeat均为 **0**，与上面的注入隔离任务分开计算。

收尾cleanupErrors为空，VISION_ONLY、ARM0、permit0、左右0、zeroSent=true，J3 **407 mm**，IR0/HOLD0。用户看到找到蓝4后慢慢修正，牌边先靠VGA右边、再靠左边，最终蓝4居中；过程中有反复修正，最后一段两轮共同前进后停，但用户对末段是否又大幅纠偏不确定。相机到标牌垂直尺量46 cm与J3末407 mm来自不同起点，不能作同基准误差计算。最后停车是60秒观察窗host STOP，不是DOCKED；关闭反馈没有证明完整搜索停靠通过，也没有同条件flow-on对照证明因果修复。详细协议审计将在下段保留。忽略目录中的旧observer仅将Quartus会话启动timeout临时设为10秒，入Session后恢复2秒；这不改变生产程序或本轮60秒运动观察预算。没有为微测试重新编译、生成SOF或重复打ZIP。

#### 真实搜索的独立审计：拒识和短转中断仍在，不能归结为传输断流

**469个ARM C样本**中，按采样可见的连续状态段计数为SEARCH3、ACQUIRE27、ALIGN18、LOST15、APPROACH4；这是稀疏读数的状态段数，不是精确动作或UART报文计数。15个APPROACH样本中仅 **1个5/5**，另有5/4四个、4/5两个、4/4八个，不能将本轮描述成“持续5/5命令但一直转”。较长同速段是任务相对时间47.276–47.798秒的六个4/4样本，邻近B读数从129转为87/64；不能用非同帧的C/B采样直接量化机械响应。

| 项目 | 本轮直接记录 | 限定解释 |
|---|---|---|
| 扫描 | 3段均+3/−3，累计1.433652秒，余13.666348秒，无反向SEARCH | 未耗尽扫描预算，无DOCKED |
| 来源有效性 | 469个ARM样本中3个sourceHealthyFresh=false，全部ACQUIRE/零速/zeroSent | 帧45034/45117/45129，inputAge54–77 ms；相应原始B帧没采到，不能归因为采集超时 |
| LOST入口 | 15次均sourceHealthyFresh=true；12次observed/locked均false，3次observed仍true而locked=false | 不是所有失锁都由源健康位或UART断流解释 |
| B帧与吞吐 | 90 B全部frameGood/fresh，无candidate/transport故障，drop恒3、discard0 | 处理38.818–57.066 ms，快照年龄40.020–92.062 ms；不是轮子响应延迟 |
| 安全与反馈 | ARM期间J3有效/实体选择一致，IR/HOLD/fatal/framing-error均0；729 C的RX全1230 | 关闭反馈状态持续，但不能由此推出运动原因已消除 |

蓝4读数经历U53→85→142→185，在右侧185–194停留较久，再回到129→64→77→末129。部分U185附近主框139..230或140..231仍有8–9像素右边余量，却已出现NF/reason4；之后U192框146..238、U194框149..239更贴右边。NF多数reason4，另有reason3和reason1各一次，因此**不能把所有拒识都称为画面裁切**。这些结果提示目标有效性变化参与了重确认，但尚未隔离其全部视觉和机械原因。

18个已采ALIGN段中11个随后进入LOST，其中6段首个样本仍为kick6，到下一LOST的板上时间差为96.095–122.530 ms。结合起步段最多60 ms，可给出这些段开始至中断的上界156.095–182.530 ms，早于名义200 ms终点：这是**目标有效性使至少这些6段提前终止的逻辑证据**，不是完整物理脉宽或车轮停止时间测量。CCTL轮询可能漏短状态；没有把样本间时间当作精确发包或机械延迟。

结论保持分层：一次隔离过渡的两轮参与运动已获用户确认；真实相机任务仍受反复对准/拒识影响而未DOCK，最后停止来自观察窗收尾。未开展匹配flow-on对照，未定位确定因果，也未据本轮改RTL、添加启动初始化或生成新版本；后续针对短暂NF的讨论不能写成已实现修复。

### E13：定向及R6通过，整板时序失败，未下载

用户授权的有限ALIGN失锁处理已落实到候选源码，BUILD_ID为 **E7070013**；正式整机顶层显式启用`ALLOW_BOUNDED_ALIGN_GAP`，旧参数兼容入口默认关闭。进入转向仍须新鲜锁定；只有原定ALIGN时长非零且 **≤200 ms** 才取得有限继续资格。健康短暂NF或同身份重新获取期间，保持已锁存的原方向、速度阶段及截止时间，不延长、不重新kick、不改向；**配置超过200 ms仍执行原先的持续锁定要求，不把整个300 ms设置都放宽**。可信有效观测跨越允许居中边界可提前停；缺失报告的旧坐标不能伪装成跨越。来源/选择/配置/帧质量/歧义/时效和原IR/J3安全条件仍优先，结束后完整零速ACQUIRE重确认。APPROACH失锁立即停车规则不变。

`build/remaining_20261104/align_continuity_e13_20261104T212612021761Z/verified_result.json`从原成功日志独立确认定向 **PASS**：新`tb_align_continuity`在TURN_SIGN−1/+1下各 **553项检查、60条UART解码**；关闭新连续性例外的旧`tb_control_repair`基线 **2041项检查、500条UART解码**。此旧基线的`STRICT_ALIGN_BAND=0`、`RUNTIME_TUNING=1`，不是旧110–130窄居中档。定向运行记录总耗时 **21.4837644秒**，最终编译/三配置日志均0 errors/0 warnings。HOST_RUNNER另有 **18项PASS**。这些均是主机/RTL证据，不是底盘实际轮速、机械过冲或停靠验收。

历史失败没有覆盖：原`result.json`因末端PASS字符串匹配漏掉冒号，把已经输出`PASS: tb_control_repair`的成功旧基线误记FAIL；`verified_result.json`只重新核对原日志，**没有重跑仿真或覆盖原FAIL文件**。此前测试台曾错误地把mode2中不适用的`cameraAbandon`作为来源故障，随后改用适用的`interactionBusy`；另一个32位回绕用例的早期失败也保留，修正细节待独立说明。不得把本次记录写成“无失败尝试”。

正式fresh课程R6已 **PASS，223.568636秒**，目标285秒、targetMet=true、cleanBuild=true；**62个新鲜source、14项正常PASS＋1项mutant CAUGHT、退出0、jobs4**。结果为`build/member_b/20261104T212711_301457Z_verilator_course/result.json`。哈希复用仍只发生在当次运行、精确source匹配条件下；新增测试进入正式回归，没有削减旧场景、帧数或断言。

E13的完整编译已结束，最终为 **FAIL**：`build/member_b/20261104T212541_740043Z_build/result.json`记录compile1309.487秒、Quartus返回0，但wrapper检测到Critical Warning332148和负setup裕量而拒绝通过。最差slow85 setup **−0.279 ns**、slow0 **−0.246 ns**，hold **+0.214 ns**；ALM29610/32070（92%）、41152寄存器、M10K357/397、DSP51/87。独立post-fit门检没有继续运行，**E13未下载、未实机，不提供可用发布SOF**。当前最后确认实板仍是E7070012，E12的真实flowoff搜索60.0067485秒未DOCK结论不变。

只读STA诊断将关键链定位为 `chassisDebugControl|mode[0] → chassis_u|shreg[19]`，经感知有效性、运动请求、安全许可和轮速ASCII转换，共21逻辑级；不是已锁存短转截止比较器。E14将signed7-bit合法轮速−15..15的绝对值/十进制串行运算改成等价查表；32768种左右/enable组合完整232位报文相等的定向验证通过，但最终时序改善必须由E14实际拟合确认。没有放宽时序约束或把仿真通过当成可下载许可。

最后迭代明确为 **E7070014**。用户允许同一最终SOF增加停车调参，以完成真实SW→红2→搜索→跟踪/前进→DOCK及近障/IR保护；E14完整构建、R6和实机验收仍待。新增策略范围和默认差异见README开头。最终ZIP等最终实际结果形成后统一打包；R5正式一页表已补齐字段，未实测成绩/等级仍PENDING。


## E14 最终源码与当前交付状态

当前开发源码为 **E7070014（最终迭代候选）**，完整构建、四角时序及最终fresh R6（233.259611秒）已PASS；实机全流程仍待本轮完成。E14完整构建和实际下载已通过，板上确认为 **E7070014**；完整红2运动任务仍待，E12保留为历史回滚。**E7070013 的定向仿真和 R6 通过，但 Full Compilation 的时序检查失败，未下载、未实机测试，不能使用其 SOF。** 以下 E12 及更早结果均属于各自历史版本，不能升级为 E14 的成绩。

E14 将用户同意的最多 200 ms 有限短转继续、最终启动配置、底盘自动反馈初始化、UART 字符查表时序修正和停车调参合并。主要验收仍是一次真实、连续的 **实体拨码选择 → 新呈现红2 → 自动搜索 → 停稳确认/跟踪 → 接近 → 自主 DOCKED 停车**，以及真实 J3 近障保护和 IR A 急停。主机观察到时限后发送 STOP 不算自主停靠；各段独立成功不能拼成完整任务。

### E14 启动、红2与安全行为

- 上电/KEY0 后为 INTEGRATED、未授权、零速。先完成一条零速运动 JSON，再在真实未 ARM、零速且 UART 空闲时发送一次 `{"T":131,"cmd":0}`，关闭 UGV 的 RAM 自动反馈。`chassisInitSent` 只表示本地完整发完最后换行字节，不是底盘执行 ACK；初始化未完成前不接受新运动任务，早按的启动不排队重放。
- KEY0 不截断正在发送的 UART 行；复位事件重新安排完整零速和初始化。若只重启底盘，待底盘启动后按 KEY0 重新初始化；系统不能自动检测所有底盘单独重启。FPGA 断电后仍须重新下载 SOF，T131 不是永久固件设置。
- 红1负责校色，蓝1–6才是车位。红2只重新读取当前合法实体选择并请求新任务，不替代拨码。复位/初始化等边界中已经留在画面内的红2不会自动启动：先移开，连续三个健康帧确认缺失，再新呈现并确认。活动任务中的红2不重复启动。
- E14 启动配置是已尝试的 E12 地面配置：search/turn/approach/fine/tolerance = **3/4/5/4/30**；短转 **200/200/60/6**（最短/最长/kick 毫秒/kick cm/s）；存储扫描预算 **15.1 s**。这是塑胶地板、历史供电/载荷条件的近似时间配置，并非新 E14 三次精确 360° 标定，也不是实验室环氧树脂地板标定。它基于两次单圈与一次双圈归一化参考，且早于关闭自动反馈；改变 search 仍使扫描资格失效。
- 仅已锁定且原定时长不超过 **200 ms** 的原地短转，可在健康短暂未识别/同身份重新获取时完成原剩余时长，不延长、重起 kick 或改向。可信坐标越过允许居中边界可提前停；坏帧、过期、错误选择/身份、歧义、近障和 A 仍立即停止。配置超过 200 ms 时保持原持续锁定要求。前进失锁仍立即停车，随后零速驻留和新三帧确认。
- **≤250 mm 的近障 HOLD 和连续三个新鲜 ≥300 mm 读数的释放规则固定**，与下面可调的正常停靠距离分离。A 是锁存急停；第一次新 POWER 只解除锁存，仍停车。DOCKED/NOT_FOUND 后退远障碍物不会自动重启。正常结束的超量程回波显示 FAr；异常/过期测距仍保护。

### E14 停车调参：同一 SOF 内设置

`tune`、`pulse` 和新增 `policy` 的写操作均要求 **VISION_ONLY、未 ARM、无运动许可、左右请求为0、完整零速已发送**。不满足时拒绝写入，不自动切模式、不自动启动；没有参数的命令只读。每次写入原子提交并独立读回；未指定的同组字段保持当前值。参数是逻辑速度/控制阈值，不是实测轮速、扭矩或机械停稳保证。

| 命令字段 | 范围与步长 | E14 上电值 | 用途 |
|---|---|---:|---|
| `tune --search` / `--turn` | 3–5 cm/s，整数 | 3 / 4 | 搜索/短转第二段；改变 search 后须重新核定扫描预算 |
| `tune --approach` / `--fine` | 4–8 / 3–4 cm/s，且 approach > fine | 5 / 4 | 远距/近距连续前进；纠偏两侧请求由控制器组合 |
| `tune --tolerance` | 10–40 px，整数 | 30 | 相对图像 U120 的允许居中范围 |
| `pulse --min-ms` / `--max-ms` | 20–300 ms，10 ms；min ≤ max | 200 / 200 | ALIGN 总时长，已包含起步段；≤200 ms 才允许有限目标间隙 |
| `pulse --kick-ms` / `--kick-speed` | 0–100 ms，10 ms / 3–8 cm/s | 60 / 6 | 起步段；0 关闭，起步时长被总时长截断 |
| `policy --corridor-px` | 45–70 px，5 px | 45 | 已锁定目标可连续前进纠偏的横向范围；不等于居中容差 |
| `policy --settle-ms` | 500–2000 ms，100 ms | 1500 | 完整零速之后的驻留，之后仍须新三帧确认 |
| `policy --stop-mm` | 300–400 mm，10 mm | 350 | 正常停靠距离比较；不是近障急停阈值，也不保证尺量终距 |
| `policy --slow-mm` | 500–1000 mm，50 mm | 500 | 切换近距前进档的距离 |

示例在空闲 JTAG 会话执行；按实际安装位置调整 Python/Quartus 路径。以下命令仅准备参数，不发送 START：

```powershell
python tools/chassis_debug.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 mode vision
python tools/chassis_debug.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 status
python tools/chassis_debug.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 tune --search 3 --turn 4 --approach 5 --fine 4 --tolerance 30
python tools/chassis_debug.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 pulse --min-ms 200 --max-ms 200 --kick-ms 60 --kick-speed 6
python tools/chassis_debug.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 policy --corridor-px 45 --settle-ms 1500 --stop-mm 350 --slow-mm 500
python tools/chassis_debug.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 policy
```

**`tune --defaults` 和 `pulse --defaults` 仍恢复通用兼容值 4/4/5/3/30 与 20/100/0/5，不是 E14 的上述启动配置。** 恢复 E14 配置请显式写入完整参数；KEY0 会恢复生产启动值并重新校色/初始化。`policy --defaults` 恰好与 E14 的 45/1500/350/500 一致。所有会话修改在 KEY0/重新下载/断电后丢失。若改变过 search，即使随后调回3，扫描资格也不会自动恢复；应按实际地面测量重新核定，不能为启动而伪称已标定。

CCTL 保持 16 个状态字。`policy` 为 opcode13，word10 高位具有能力标记和17位参数；旧固件没有能力标记时主机拒绝写入。word10 低位保留原标志以及初始化支持/本地发送完成位。策略写入不更改速度、pulse、扫描资格/预算，不刷新注入租约，不直接写轮速或测距。


本节为E14候选实现和待执行操作说明，实际测量结果将在后续独立追加，不覆盖E13失败或E12历史记录。

### E14 正式R6首轮：Verilator工具崩溃，保留FAIL

`build/member_b/20261104T220131_947405Z_verilator_course/result.json`为 **FAIL，104.45794秒、exit1、targetMet=false**。失败点是新增`tb_chassis_init`的Verilator编译阶段：0.095982秒返回3221225477（Windows **0xC0000005**访问冲突），不是该测试的运行时断言失败，也不是完整套件耗尽时间。日志的通用错误文本包含“compilation failed or exceeded deadline”，但该次返回码/用时支持前者。原始FAIL与日志保留，不能因为不足285秒就称达标。

后续仅作等价测试台兼容修正，保留初始化场景及断言，生产RTL不改；最终完整fresh R6仍须重新执行并独立记录。Quartus E14完整编译继续，不能从该仿真工具崩溃推断FPGA时序或实机结果。


### E14 R6工具兼容修正与第二轮整体超时

首轮崩溃后，仅把`tests/member_c/tb_chassis_init.sv`内两处层次枚举引用`dut.SEND`/`dut.LOAD_FB`改为相同编码的本地常量；生产RTL、初始化场景及断言未削减。独立Verilator验证 `verilator_init_verified_20261104T220628_233730Z/result.json` 已PASS：4939项检查、183条完整UART、41条初始化报文及32768个ASCII等价组合，约8.21秒。它仅验证兼容修正后的初始化场景，不替代完整R6。

第二轮fresh R6 `build/member_b/20261104T220649_240451Z_verilator_course/result.json`仍为 **FAIL，301.821791秒、exit1、targetMet=false**。已完成10项PASS，包括全部新增场景、debug/red2和continuous；`perceptionCoreOverload_tb`运行时触及整个套件300秒时限而终止，后续场景未完成。不能写成17项PASS或285秒达标，且前两轮失败均保留。

该轮与Quartus拟合并行；主机争用是待核对的耗时因素，不是已确认唯一原因。计划拟合结束后、生产源码不变时重新执行完整fresh R6，再独立记录实际总耗时。未删除负载场景、未降低帧数/断言、未改285秒目标，也不跨运行复用旧二进制冒充clean build。该第二轮结束时E14尚未下载；后续下载结果另列。

### E14 candidate source publication / E14候选源码推送

按用户要求，编译进行时先推送当前冻结候选源码，后续实测结果可独立追加。README已合并成单个逐节中英对应文件，独立英文文件删除；保留15个主节、37个子节和原英文独有说明。发布白名单/fixture同步，submission14项(0.287s)、结构6项(2.038s)和实际60依赖/53bench结构检查PASS。当前仍是E14构建运行中、未下载；R6两轮FAIL如实保留。不发布未过时序的E14 SOF，不生成已验收最终ZIP。

At the user’s request, publish the frozen candidate sources during compilation; later hardware results may follow in another commit. One section-paired bilingual README retains15 main sections,37 subsections and all English-only content. The export/structure contract was updated;14 submission tests(0.287s),6 structure tests(2.038s) and the actual60-dependency/53-bench structural check passed. E14 compilation is still running and it is not programmed; both R6 failures remain recorded. No unqualified E14 SOF or validated final ZIP is published.

### E14完整构建与四角时序通过 / E14 full build and four-corner timing passed

**中文**

最终E14 `build/member_b/20261104T220114_044911Z_build/result.json`已 **PASS**：Full Compilation **1333.597秒**，独立post-fit门检 **25.925秒**，0 errors、93 warnings。四角最差setup **+1.136 ns**、hold **+0.118 ns**；reportGate检查88项、未约束项目全0。ALM **31016/32070（97%）**、41154寄存器、357/397 RAM、51/87 DSP、2 PLL。资源余量较小；同步链覆盖通过，但MTBF仍未评估。E13负裕量失败不被改写，这次E14自己的完整拟合/门检才提供时序通过证据。

[E14 SOF](../firmware/E7070014/PartBDebug.sof)为成功build原始产物的逐字节副本，**6706155字节**，SHA256 `f74a3ff85a8543ac6a204d48d4a0a578189ca77a134c444a92d4a2c7920e5aba`。复制前执行当前源码/成功build绑定校验，未重新生成或改写SOF。E12副本保留为历史回滚；E14下载、板上身份及真实任务结果须另列，不因build通过自动成立。R6两轮失败保留，拟合结束后的fresh完整复跑与真实红2全流程仍待其自身结果；不生成“已完成整机验收”的ZIP。

**English**

Final E14 `build/member_b/20261104T220114_044911Z_build/result.json` is **PASS**: Full Compilation **1333.597 seconds**, independent post-fit gate **25.925 seconds**,0 errors and93 warnings. Across four corners, worst setup is **+1.136 ns**, hold **+0.118 ns**; reportGate evaluated88 checks with all unconstrained categories zero. Resources: **31016/32070 ALMs(97%)**,41154 registers,357/397 RAM blocks,51/87 DSPs and2 PLLs. Logic headroom is small; synchronizer coverage passed, while MTBF remains unassessed. E13's negative-slack failure is preserved; these are E14's own accepted fit/timing results.

The [E14 SOF](../firmware/E7070014/PartBDebug.sof) byte-matches the successful original artifact: **6706155 bytes**, SHA256 `f74a3ff85a8543ac6a204d48d4a0a578189ca77a134c444a92d4a2c7920e5aba`. Current-source/successful-build binding was checked before copying; no SOF content was regenerated or modified. E12 remains a historical rollback copy. Programming, board identity and physical task results require separate evidence. Both failed R6 attempts remain; the fresh complete run after fitting and real red2 end-to-end task await their own results. No archive is labelled as fully hardware-accepted.

### E14实际下载与零速预检 / E14 programming and stationary preflight

**中文**

`build/member_b/20261104T222420_281401Z_program/result.json`记录E14实际下载 **PASS**，`programmerSucceeded=true`、`buildIdVerified=true`，完成于2026-11-05 **09:24 AEDT**（UTC2026-11-04T22:24:28.724781）。实际板上已更新为 **E7070014**，不是仅复制SOF。

独立只读 `e14_initial_preflight.json` 的4/4真实蓝4样本均observed、locked、sourceHealthyFresh、calibrated；VISION_ONLY、ARM0、无许可、左右0、zeroSent。初始化supported/sent均true，RX计数四次均0；这说明初始化本地完成及该窗口接收静默，不是底盘ACK或长期流量保证。生产启动tune3/4/5/4/30、pulse200/200/60/6、scan15.1 s且资格true、policy45/1500/350/500全部读回一致。

J3当时真实读数 **167–180 mm**、HOLD=true，所以没有启动最终搜索；该预检不证明完整红2搜索停靠通过，也不把近距遮挡当成软件失败。后续运动结果独立记录。

**English**

`build/member_b/20261104T222420_281401Z_program/result.json` records actual E14 programming **PASS**, with `programmerSucceeded=true` and `buildIdVerified=true`, completed **09:24 AEDT on5 November2026** (UTC2026-11-04T22:24:28.724781). The board is now **E7070014**, beyond merely copying its SOF.

Independent read-only `e14_initial_preflight.json` retained4/4 actual blue4 observations, all observed, locked, sourceHealthyFresh and calibrated. All were VISION_ONLY/disarmed/no permit/L0/R0/zeroSent. Initialization supported/sent were true and RX remained0 in all four polls: local completion and a quiet observed window, not a chassis ACK or long-term traffic guarantee. Readback matched production tune3/4/5/4/30, pulse200/200/60/6, qualified15.1-second scan, and policy45/1500/350/500.

Actual J3 was **167–180 mm**, with HOLD=true; the final search was therefore not started. This stationary preflight does not establish a complete red2 search-to-dock task or diagnose the close reflection as a software failure. Subsequent motion results remain separate.

### E14最终fresh R6通过233.259611秒 / Final fresh E14 R6 passed in233.259611 seconds

**中文**

`build/member_b/20261104T222424_503862Z_verilator_course/result.json`记录正式 **PASS，233.259611秒**，`targetMet=true`、exit0、cleanBuild=true；比用户285秒目标少 **51.740389秒**。**17个正常场景全部PASS，破坏锁定的`targetTracker_broken_lock`被CAUGHT**，共18项，无超时。运行源码提交为 `24f7abcdf7c0f777a596dfc8e9aeea13c3b3d03d`；65个fresh源文件、17次真实编译，overload仅复用本次continuous精确相同编译输入的二进制。

沿用原wrapper、jobs4、单编译器/最多两并行仿真和300秒硬限，没有跨运行缓存、移除负载/负测试或减少帧数/断言。新增有限ALIGN、初始化、启动门与policy场景均通过；初始化的4939项检查及32768种ASCII等价组合保留。此前首轮工具崩溃FAIL104.45794秒、第二轮整体deadline FAIL301.821791秒仍保留，第三轮在Quartus全部退出、启动前CPU约17%时独立通过，不用新PASS覆盖原FAIL。

正式R6证明本次软件模型/RTL回归范围及用时，**不是整车全流程实测通过**。E14已另有完整构建/四角时序、实际下载/身份、4/4零速视觉及启动参数读回证据；真实SW→红2→画外搜索→接近→DOCK和最终近障实测仍由主线独立记录。本次按用户要求立即补记录并推送，不等待整轮运动测试结束。

**English**

`build/member_b/20261104T222424_503862Z_verilator_course/result.json` records formal **PASS in233.259611 seconds**, `targetMet=true`,exit0 andcleanBuild=true, **51.740389 seconds below the requested285-second target**. **All17 normal scenarios passed; `targetTracker_broken_lock` was CAUGHT**,18 total with zero timeouts. The run used source commit `24f7abcdf7c0f777a596dfc8e9aeea13c3b3d03d`:65 fresh source files and17 actual compilations. Overload reused only this same run's continuous binary with exactly matching compilation inputs.

The original wrapper,jobs4,one compiler/at most two concurrent simulations and300-second hard deadline were retained. No cross-run cache, overload/negative-test removal or reduced frame/assertion coverage was used. Bounded ALIGN, initialization,start gate and policy scenarios passed;4939 initialization checks and32768 ASCII-equivalence combinations remain. The earlier104.45794-second tool-crash FAIL and301.821791-second suite-deadline FAIL are preserved. This third run passed independently after all Quartus processes had exited, with approximately17% CPU before launch; it does not overwrite failed attempts.

R6 establishes the stated model/RTL regression and runtime, **not complete vehicle acceptance**. E14 separately has full-build/four-corner timing, actual programming/identity and4/4 stationary vision/startup-readback evidence. Physical SW→red2→outside-view search→approach→DOCK and final obstacle trials are recorded independently by the hardware task. Per the user's instruction, these R6 results are pushed immediately without waiting for all motion testing.

### E14首轮真实红2搜索未完成 / First real E14 red2 search remained incomplete

**中文**

`integrated_blue4_e14_red2_search_to_dock_01.jsonl`保留 **728个C、91个B快照**，真实红2确认使请求tag4→5并ARM进入SEARCH；**host START、合成写入和heartbeat均0**。首次ARM后的观察 **60.0170459秒**，结果 **INCOMPLETE**、未DOCK。完整日志中464个ARM样本为 **64个SEARCH、400个HOLD**，observed/locked均0，没有采到ACQUIRE、ALIGN、APPROACH或DOCK。最终搜索命令累计 **8.230596秒**，尚余 **6.869404秒**，未耗尽15.1秒扫描预算。起步J3约725 mm；主机相对42.473秒先采到49 mm并HOLD，42.793秒FAR后短恢复，43.623秒167 mm进入长HOLD；94.514秒后短暂恢复，直到观察窗结束。最终观察窗到限后STOP→VISION_ONLY收尾，ARM0、左右0、zeroSent、J3 732 mm、HOLD=false，cleanupErrors为空。

用户反馈“超过蓝四没停车”。约38.08秒的一个B快照有蓝候选框x83..170/y48..119，却因reason4被拒绝；它不是接受的蓝4目标，且约1秒间隔的B采样不能证明所有中间帧或唯一失败原因。不能将本轮写成成功抓牌后跟踪、接近或自主停靠。真实红2到新请求/SEARCH链路和近障保护均有板上证据，但完整任务仍未通过。

独立静止policy实机写入 **50 px /1400 ms /360 mm /550 mm** 并读回，再恢复 **45/1500/350/500**，两次CLI exit0、维持零速。证据为`e14_policy_stationary_write.json`和`e14_policy_stationary_restore.json`。这证明四个新字段的板上写入/读回/恢复，不是这些参数的运动性能验收。主线继续在同一个E14 SOF内调参，结果分轮保留。

**English**

`integrated_blue4_e14_red2_search_to_dock_01.jsonl` retained **728 C and91 B snapshots**. A real red2 confirmation changed request tag4→5 and armed SEARCH, with **zero host START, synthetic writes or heartbeat commands**. The observation after first ARM lasted **60.0170459 seconds**, ending **INCOMPLETE**, without DOCKED. The complete log has464 armed snapshots: **64 SEARCH and400 HOLD**, all targetObserved/locked=false, with no ACQUIRE,ALIGN,APPROACH or DOCK sampled. Final accumulated scan-command time was **8.230596 seconds**, leaving **6.869404 seconds**; the15.1-second scan budget was not exhausted. J3 started around725 mm. At host-relative42.473 seconds it sampled49 mm/HOLD; a FAR reading allowed brief recovery around42.793 seconds, then167 mm at43.623 seconds began a long HOLD. Brief recovery occurred after94.514 seconds until the observation limit. At the observation limit, STOP→VISION_ONLY cleanup ended disarmed,L0/R0,zeroSent,J3 732 mm,HOLD=false, with no cleanup errors.

The operator reported that the robot passed blue4 without stopping for it. One B snapshot around38.08 seconds contained a blue candidate atx83..170/y48..119 rejected withreason4. It was not an accepted blue4 target; roughly one-second B sampling cannot establish every intervening frame or a unique cause. This is not accepted-target tracking, approach or autonomous docking success. Real red2→new request→SEARCH and close-obstacle protection have board evidence; the complete task remains unpassed.

An independent stationary hardware policy write/readback changed all four fields to **50 px/1400 ms/360 mm/550 mm**, then restored **45/1500/350/500**. Both CLI calls exited0 and remained zero, recorded in `e14_policy_stationary_write.json` and `e14_policy_stationary_restore.json`. This verifies writing, reading and restoring the four fields, not their motion performance. Further tuning uses the same E14 SOF and retains each trial separately.

完整日志复核修正：早先49个SEARCH/6.552069秒来自中途快照，不能当最终统计；现以上述64/400与8.230596秒为准。此次是记录修正，没有重跑或改程序。

Full-log correction: the earlier49 SEARCH/6.552069-second figures came from an intermediate snapshot, not final totals. The64/400 and8.230596-second totals above supersede them. This corrects the record without rerunning hardware or changing the program.
