# ECHO-7 本次修复与实机记录

日期：2026-11-04（Australia/Sydney）。工作工程：`C:/Quartus_Projects/ECHO72.0/github_publish/MTRX3700_MajorProject`，基线 `dc1db23`。外层旧 B 工程及其未提交 QSF 修改未覆盖。当前源码版本 `E7070004`，CCTL 接口版本 `E7070001`。下文保留各版实际证据：E7070003修正现场单帧溢出恢复，E7070004修正红2启动早于新目标三帧锁定的问题。

## 当前结论与证据边界

当前 E7070004 的控制定向仿真 **254检查PASS**，完整干净副本 R6 **12 PASS + CAUGHT，219.556074秒**，满足用户285秒目标。Full Compilation **1121.141秒PASS**，post-fit门检 **25.868秒PASS**；ALM29576/32070（92%），最差setup/hold **+1.633/+0.118 ns**，未约束项0。该版新SOF于 **22:31:50 AEDT** 下载成功并读回 **E7070004**；真实红2重新选择、等新锁定、ARM/ALIGN的板上链路通过，用户确认实物启动，并最终澄清“蓝一脱离后就停车了”。末状态为VISION_ONLY、未ARM、左右逻辑零速，用户确认已经停止。主机两秒观察后STOP的独立机械停车时刻未测，不据此宣称两秒实物定时停车；002架空轮子/IR观察仍保留为该版独立记录。

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

详细开关、IR、模式及可执行命令见根目录 [中文README](../README.md) / [English README](../README_EN.md)。一页数据表发布为 [ECHO7_Integrated_Datasheet.pdf](ECHO7_Integrated_Datasheet.pdf)，对应展示指标保存在 [integrated_datasheet_metrics.json](integrated_datasheet_metrics.json)。数据表使用最终用户澄清后的结论；未完成的落地指标及独立停车时刻测量明确保留，不用板上状态替代。

### 关键现场修正的先后顺序

1. **先修基础控制和接口，再构建集成顶层。** 选择、健康资格、三帧锁定、实际零速发送、IR新按压和J3新测量是前置条件；没有把主机注入做成绕过控制器的直接轮速写入。
2. **用户追加红2动作需求。** 附件旧NO_ACTION不再适用；增加重新选择、授权窗口、专用交互边界复位和旧事件时间过滤。首轮资源报告超限后只做候选诊断分页调整。
3. **E7070002先通过构建与架空动作，再暴露候选溢出永久阻断。** 用户移动裁切标牌确实改善了画面，但不能修复历史sticky位永久禁止健康的逻辑问题，因此需要003代码修正。
4. **E7070003在实板验证恢复，然后真实红2又暴露启动过早。** 请求tag确实改变，问题发生在第一健康帧与第三帧锁定之间；终态不自行重启是预期安全行为，不能通过取消这一限制掩盖早起问题。
5. **E7070004只收紧未标定红2启动资格。** 新增针对前两帧等待/第三帧启动的断言，重新通过完整R6、Full Compilation和四角门检，新SOF已下载并读回版本。真实红2实测tag3→4，在新锁定后ARM/ALIGN；不发心跳仍保持正式模式授权，短暂视觉丢失时逻辑零速重确认，最后STOP读到零速发送完成。用户先反馈不会自动停车，随后澄清蓝1脱离后已实际停车；最终VISION_ONLY/未ARM且实物已停。零速发送完成本身不等于实物停稳，用户观察独立记录。

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
| 最终文档/提交导出 | README三件精确白名单；结构测试6项PASS（1.613秒），实际48个bench/60个依赖检查PASS；已有submission测试14项PASS（0.226秒） | 导出包括README_EN及指标JSON；OWNERS覆盖277个源文件。属于发布工具检查，不累计为新RTL或实机测试 |

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

上面的下载命令说明本机复现入口，实际执行事实以各版“构建与实机”的时间、版本和日志为准。当前CLI核对`last_build.json`中的原始产物身份，不接受任意路径副本；从Git取得发布固件的读者应按README的Quartus Programmer流程加载`firmware/E7070004/PartBDebug.sof`，或在本机重新构建后使用新生成的原始路径。下载前应先确保底盘安全放置，并按README选择模式。

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

当前实现是累计获准SEARCH转动命令时间的有界扫描，另有120秒任务总超时。没有已验证的本机航向回包，也没有三次地面一圈时间标定。[UGV02官方文档](https://www.waveshare.com/wiki/UGV02)提供IMU/底盘反馈查询，但不能据此假定当前固件字段、单位或更新率已验证。

默认10秒只用于显式启动的CHASSIS_INJECT有界调试。正式INTEGRATED在未标定时禁止无目标360°扫描，目标已经可靠可见时仍能正常对准接近。架空轮转不能标定地面360°，零速JSON发送完成也不能证明车体物理停稳。

仍需人工完成：同一地面三次扫描标定及误差；六车位逐个落地闭环、350 mm停靠误差、任务时间和图像到UART延迟；实物J3危险/无回波及250/300/350 mm边界专项验证（本次边界在管脚模型/控制TB验证，实物主要读取有效距离）；SW8正常/旁路三次公平对照；连续移动/遮挡/不同光照；缺失A/C成员SID。004真实红2观察窗口仍有短暂LOST/ACQUIRE，长期视觉稳定性未解决；frame30321蓝6颜色区域碎裂也保留为已知识别缺陷。

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

用户明确回答SW6能看到候选的颜色信息。该反馈确认候选颜色诊断在实物屏幕上可见，但用户尚未理解/确认翻页，因此**两页自动切换仍未实物确认**；UNKNOWN、拒识原因以及所有16槽的实际显示也没有得到明确确认，不能从“候选颜色可见”推断这些项目已通过。此前分页/拒识的RTL测试结果继续保留为仿真证据。

用户明确确认SW7：中心落在白色空隙时能看到采样颜色，并显示“无标牌”。这项实际空白中心场景已确认，与同帧图中的中心空隙一致；它是局部采样和覆盖身份提示，不是中心独立OCR，也不扩大为已经验证中心覆盖所有数字或歧义场景。此次只追加用户目视结果，没有新的JTAG、RTL或运动试验。

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

- **已增加实物覆盖：**六个实体独热档位及NO_SELECTION/CONFLICT的零运动视觉验证；当前完整六牌各12/12接受；SW6候选颜色可见和SW7白色中心“无标牌”；真实J3架空前进/减速/正常DOCKED、退远不重启；HOLD03危险停止、迟滞保持、退远恢复及独立STOP，均按各自输入层和用户观察范围记录。
- **真实无回波仍未观察：**现有J3快照不能替代无回波、超时输入的实物专项测试。危险/迟滞/停靠功能通过，也不等于完成精确尺子标定或机械停车误差测量。
- **显示与旁路仍有待项：**SW6两页自动切换、UNKNOWN/拒识原因及完整16槽尚未获明确实物确认；SW7中心实际覆盖标牌身份/歧义场景未确认；SW8正常/旁路三对相同场景公平对照仍未完成。
- **地面与长期性能仍有待项：**同一地面三次一圈时间标定及误差，六车位真实视觉落地搜索/对准/接近/停靠闭环，任务时间、图像变化到UART延迟、实际停车误差，以及持续移动/遮挡/光照变化。当前坏帧仍可能发生，441次选择记录中的7个候选溢出和间歇丢锁未被删除；新好帧后的恢复不等于图像永不失败。
- **归属信息：**A/C成员SID仍待本人补齐，不虚构成员身份或人工签核。上述新增硬件结果没有要求重新编译生产RTL，也没有改写已取得的E7070004 R6/Full Compilation数据。
