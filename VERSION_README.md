# ECHO-7 版本记录 / Version history

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

## E14 final source and delivery status

Current development sources are **E7070014, the final iteration candidate**. Its full build, four-corner timing and final fresh R6(233.259611 seconds) have passed; complete physical-task acceptance remains pending. **E7070014 has passed the full build and actual programming/identity check; complete red2 physical-task acceptance remains pending. E7070012 is retained for historical rollback. E7070013 passed focused simulation and R6 but failed Full Compilation timing and was never programmed; do not use its SOF.** E12 and earlier results below retain their original version scope.

E14 combines the approved at-most-200 ms turn continuity rule, startup profile, chassis telemetry initialization, UART ASCII lookup timing repair and stationary tuning. Main acceptance is one real uninterrupted **physical switches → newly presented red2 → automatic search → stopped confirmation/tracking → approach → autonomous DOCKED stop**, plus real J3 near-obstacle and IR A protection. Host STOP at an observation deadline is not autonomous docking; independent successful segments do not form a complete task.

### E14 startup, red2 and safety behavior

- Boot/KEY0 starts INTEGRATED, disarmed and zero. After completing a full zero-speed motion JSON, the truly disarmed, zero, idle serializer sends `{"T":131,"cmd":0}` once to disable UGV RAM automatic telemetry. `chassisInitSent` means the local final newline byte has completed, not a chassis execution ACK. New tasks are gated until initialization completes; early starts are discarded rather than queued.
- KEY0 does not truncate an in-flight UART line; it schedules a new complete zero/configuration sequence. After a chassis-only reboot, wait for chassis startup then press KEY0. The design does not detect every chassis-only reboot automatically. FPGA power loss still requires SOF programming. T131 is not persistent firmware configuration.
- Red1 calibrates colour, blue1–6 identify bays, and red2 rereads the valid physical selection and requests a new task. A red2 left visible across reset/initialization cannot automatically start: remove it for three healthy absence frames, then present it anew for confirmation. It does not restart an active task.
- Production boot uses the tried E12 profile: search/turn/approach/fine/tolerance **3/4/5/4/30**, ALIGN **200/200/60/6** (minimum/maximum/kick ms/kick cm/s), stored scan budget **15.1 s**. This is a historical approximate plastic-floor time profile for the tested supply/load, not three new E14 precise 360-degree trials or an epoxy-floor calibration. Its basis is two single circles plus one normalized double-circle reference, measured before feedback shutdown. Changing search speed still invalidates scan qualification.
- Only an already locked original turn with total duration **≤200 ms** may finish its remaining time through healthy temporary not-found/same-identity reacquisition. No extension, re-kick or reversal is allowed. A trusted crossing can stop early; bad/stale/ambiguous input, wrong selection/identity, close obstacles and A still stop immediately. Longer configured turns retain continuous-lock requirements. APPROACH target loss still stops immediately, followed by zero dwell and three new confirmation frames.
- The **≤250 mm obstacle HOLD and three fresh ≥300 mm readings for release remain fixed**, independently of adjustable normal docking distance. A latches an emergency stop; the first fresh POWER only clears that latch and leaves the robot stopped. Retreating an obstacle after DOCKED/NOT_FOUND cannot restart the task. A normally completed out-of-range echo reports FAr; abnormal/stale ranging remains protected.

### E14 stationary tuning in the same SOF

Writes through `tune`, `pulse` and new `policy` require **VISION_ONLY, disarmed, no motion permit, both requests zero and a completed zero packet**. Otherwise they are rejected without changing mode or starting motion. Commands without fields only read. Each write is atomic and separately read back; unspecified fields in that group retain current values. These are logical speeds and control thresholds, not measured wheel speeds, torque commands or guaranteed mechanical settling times.

| Field | Range and step | E14 boot | Purpose |
|---|---|---:|---|
| `tune --search` / `--turn` | Integer 3–5 cm/s | 3 / 4 | Search / second-stage ALIGN; changing search invalidates scan qualification |
| `tune --approach` / `--fine` | 4–8 / 3–4 cm/s; approach > fine | 5 / 4 | Far/near continuous forward requests; controller derives steering pairs |
| `tune --tolerance` | Integer 10–40 px | 30 | Allowed centred error about image U120 |
| `pulse --min-ms` / `--max-ms` | 20–300 ms, step10; min ≤ max | 200 / 200 | Total ALIGN duration including kick; finite target-gap exception only at ≤200 ms |
| `pulse --kick-ms` / `--kick-speed` | 0–100 ms, step10 / 3–8 cm/s | 60 / 6 | Startup stage; zero disables it, total duration truncates it |
| `policy --corridor-px` | 45–70 px, step5 | 45 | Locked-target horizontal range for continuous forward steering, distinct from centring tolerance |
| `policy --settle-ms` | 500–2000 ms, step100 | 1500 | Dwell after a complete zero, before new three-frame confirmation |
| `policy --stop-mm` | 300–400 mm, step10 | 350 | Normal docking comparison, not emergency range or guaranteed ruler gap |
| `policy --slow-mm` | 500–1000 mm, step50 | 500 | Distance for switching to near forward speed |

Use an idle JTAG link and adjust installed paths. These commands prepare settings without issuing START:

```powershell
python tools/chassis_debug.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 mode vision
python tools/chassis_debug.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 status
python tools/chassis_debug.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 tune --search 3 --turn 4 --approach 5 --fine 4 --tolerance 30
python tools/chassis_debug.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 pulse --min-ms 200 --max-ms 200 --kick-ms 60 --kick-speed 6
python tools/chassis_debug.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 policy --corridor-px 45 --settle-ms 1500 --stop-mm 350 --slow-mm 500
python tools/chassis_debug.py --quartus-bin C:/intelFPGA_lite/18.1/quartus/bin64 policy
```

**`tune --defaults` and `pulse --defaults` still restore generic compatibility values 4/4/5/3/30 and 20/100/0/5, not the E14 production boot profile above.** Restore E14 explicitly with the full fields; KEY0 restores production startup values and restarts calibration/initialization. `policy --defaults` does match E14's45/1500/350/500. Session changes are volatile across KEY0/reprogramming/power loss. Changing search back to3 does not automatically restore invalidated scan qualification; re-establish it from the actual floor rather than asserting calibration merely to start.

CCTL remains16 words. Opcode13 writes policy; word10 upper bits carry a capability marker and17-bit payload, while low bits retain previous flags and initialization support/local completion. Host tools refuse policy writes on older unsupported firmware. A policy write does not alter speed/pulse/scan settings, refresh an injection lease, override wheels or fabricate ranging.

### E14 已完成的定向验证（尚非整板或实机验收）

冻结源码的定向结果 `motion_policy_20261104T220025097074Z/result.json` 为PASS、18.9839668秒：四字段策略覆盖11616种合法组合、11687项检查；debug251项；真实adapter/control基线2049项及500条完整UART；初始化启动门47项。随后 `motion_policy_20261104T220112003036Z/result.json` 的最终debug254项另覆盖生产启动值与KEY0恢复。主机工具31项、HOST_RUNNER18项通过。正式R6的17个正常场景加mutant已在最终fresh运行通过（233.259611秒），最终Quartus时序也另行通过；完整实机仍待，不以仿真替代。

### Completed focused E14 checks (not full-build or hardware acceptance)

The frozen-source focused result `motion_policy_20261104T220025097074Z/result.json` passed in18.9839668 seconds:11616 legal policy combinations and11687 assertions,251 debug checks,2049 real adapter/control checks with500 complete UART lines, and47 initialization-start gate checks. The subsequent `motion_policy_20261104T220112003036Z/result.json` passed254 final debug checks including production boot values and KEY0 restoration. Host tools passed31 tests and HOST_RUNNER passed18. Formal R6 completed all17 normal scenarios plus the mutant in the final fresh run(233.259611 seconds); final Quartus timing also passed independently. Complete physical-task acceptance remains pending.

### E14 正式R6首轮：Verilator工具崩溃，保留FAIL

`build/member_b/20261104T220131_947405Z_verilator_course/result.json`为 **FAIL，104.45794秒、exit1、targetMet=false**。失败点是新增`tb_chassis_init`的Verilator编译阶段：0.095982秒返回3221225477（Windows **0xC0000005**访问冲突），不是该测试的运行时断言失败，也不是完整套件耗尽时间。日志的通用错误文本包含“compilation failed or exceeded deadline”，但该次返回码/用时支持前者。原始FAIL与日志保留，不能因为不足285秒就称达标。

后续仅作等价测试台兼容修正，保留初始化场景及断言，生产RTL不改；最终完整fresh R6仍须重新执行并独立记录。Quartus E14完整编译继续，不能从该仿真工具崩溃推断FPGA时序或实机结果。

### First formal E14 R6: Verilator tool crash, FAIL retained

`build/member_b/20261104T220131_947405Z_verilator_course/result.json` is **FAIL,104.45794 seconds,exit1,targetMet=false**. Verilator compiling new `tb_chassis_init` returned3221225477 (Windows **0xC0000005**, access violation) after0.095982 seconds. This was not a runtime assertion failure or an exhausted suite deadline. The generic error text says compilation failed or exceeded the deadline; this return code and duration establish the compile failure. The original FAIL/logs remain and being below285 seconds does not make it a passing result.

Only equivalent testbench compatibility changes are planned, retaining initialization scenarios/assertions and unchanged production RTL. A fresh complete R6 still needs its own result. The E14 Quartus build continues independently; this simulator crash does not determine FPGA timing or physical behavior.

### E14 R6工具兼容修正与第二轮整体超时

首轮崩溃后，仅把`tests/member_c/tb_chassis_init.sv`内两处层次枚举引用`dut.SEND`/`dut.LOAD_FB`改为相同编码的本地常量；生产RTL、初始化场景及断言未削减。独立Verilator验证 `verilator_init_verified_20261104T220628_233730Z/result.json` 已PASS：4939项检查、183条完整UART、41条初始化报文及32768个ASCII等价组合，约8.21秒。它仅验证兼容修正后的初始化场景，不替代完整R6。

第二轮fresh R6 `build/member_b/20261104T220649_240451Z_verilator_course/result.json`仍为 **FAIL，301.821791秒、exit1、targetMet=false**。已完成10项PASS，包括全部新增场景、debug/red2和continuous；`perceptionCoreOverload_tb`运行时触及整个套件300秒时限而终止，后续场景未完成。不能写成17项PASS或285秒达标，且前两轮失败均保留。

该轮与Quartus拟合并行；主机争用是待核对的耗时因素，不是已确认唯一原因。计划拟合结束后、生产源码不变时重新执行完整fresh R6，再独立记录实际总耗时。未删除负载场景、未降低帧数/断言、未改285秒目标，也不跨运行复用旧二进制冒充clean build。该第二轮结束时E14尚未下载；后续下载结果另列。

### E14 R6 tool compatibility fix and second-run overall timeout

After the first crash, only two hierarchical enum references, `dut.SEND`/`dut.LOAD_FB` in `tests/member_c/tb_chassis_init.sv`, were replaced with same-encoding local constants. Production RTL, initialization cases and assertions were unchanged. Independent Verilator validation `verilator_init_verified_20261104T220628_233730Z/result.json` passed4939 checks,183 complete UART lines,41 initialization lines and32768 ASCII-equivalence combinations in about8.21 seconds. This validates the repaired scenario, not complete R6.

The second fresh R6, `build/member_b/20261104T220649_240451Z_verilator_course/result.json`, is **FAIL,301.821791 seconds,exit1,targetMet=false**. Ten scenarios completed PASS, including all new scenarios, debug/red2 and continuous operation. `perceptionCoreOverload_tb` was terminated at the whole-suite300-second deadline; later scenarios did not complete. This is neither17 PASS nor a met285-second target. Both failed runs remain preserved.

This run overlapped Quartus fitting. Host contention is a timing factor to investigate, not an established sole cause. The plan is another complete fresh R6 after fitting, with unchanged production sources and a separately recorded duration. No overload case, frame count or assertion is removed, the285-second target remains, and old cross-run binaries are not reused as a clean build. At the end of that second run, E14 was not yet programmed; subsequent programming is recorded separately.

## E12 及此前历史记录

截至下述E12历史轮次，发布版本为 **E7070012**；该轮只补充同SOF/同参数的实机记录，没有新RTL、编译或R6。原正式R6 **223.404755秒（13 PASS＋CAUGHT）**、Full Compilation1163.903秒＋post-fit26.783秒、下载及静止pulse读写证据保留。此前第七轮从约41 cm重新POWER的独立任务达到DOCKED，J3 292 mm与探头前端尺量约370 mm差异未定；它不能替代60 cm或画外搜索闭环。其余真实搜索失败、左右起步/过冲问题仍按轮次记录。

后续OLED确认UGV Rover/version0.9，同E12重下载并恢复实验tune3/4/5/4/30、pulse200/200/60/6及15.1秒基准。T131仅关闭底盘RAM自动反馈，独立零速RX由约11 kB/s变为五样本0新增。连续改值trial1因真实500 mm诊断边界提前结束且没有物理验收；trial2已观察5/5→5/4→5/5三段，用户确认较快→较慢→较快→停车。单次ALIGN→完整零速驻留→APPROACH隔离也取得逻辑证据，用户确认“两侧轮子都一起走的”。这些是限定试验结果，不是精确轮速、直行精度或flowoff因果修复证明。

紧接着的一轮**真实相机画外搜索仍INCOMPLETE，60.0067485秒未DOCK**，由观察窗结束后的host STOP收尾；729 C/90 B、host START/合成写入/heartbeat均0。用户看到找到蓝4后反复修正、牌先到右边再到左边、最后居中，末段两轮共同前进后停；是否又发生大幅末段纠偏不确定。用户尺量**相机到标牌垂直距离46 cm**，板上J3末读数**407 mm**，测量起点不同，不能计算为同基准误差。收尾V1未ARM、permit0、左右0、zeroSent、IR0/HOLD0且cleanup无错误。实验组合仍不是推荐设置；完整搜索停靠未通过，原因未证实。SOF复位默认未改，不新增E13初始化或重复搜索结论。

> 历史E11源码及当时实板E7070011已独立构建/下载；该轮发布为E11，当前发布为E12。控制runtime两sign996/358、legacy847/289；首R6 FAIL302.015209保留，fresh最终R6 PASS219.199994秒/13 PASS＋CAUGHT；编译1375.853秒＋门检26.278秒PASS。真实JTAG停车调参及标定失效/默认恢复PASS、蓝4零速4/4锁定；初始停车调参未运动；后续首轮/search3搜索均NOT_FOUND，turn3仅抽动INCOMPLETE。当前3/5/4/3/40与15.1秒为volatile实验参数，turn5已INCOMPLETE，approach4亦INCOMPLETE，降速未解决过冲；停止本轮测试，RTL不再改版。

> 历史E10的源码、成功构建及当时实板均为E7070010，最终VISION_ONLY、未ARM、零速。E10默认居中U90–150并增加锁定目标直接APPROACH入口；本版定向默认两sign各804/275、旧参数817/278已PASS（29.1663517秒）；正式R6已PASS271.31444秒、13 PASS＋CAUGHT；Full Compilation1260.493秒＋post-fit25.832秒PASS，setup/hold +0.909/+0.118ns，实际下载读回E10；蓝4零速预检4/4锁定，实机短暂APPROACH后LOST/恢复SEARCH，最终NOT_FOUND/SCAN_BUDGET，未DOCK、未触发反向SEARCH；失锁恢复问题保留。历史构建和失败证据保留。E9有限回扫的两种TURN_SIGN各696检查/245UART PASS，累计执行20.8500433秒；正式R6独立PASS274.530007秒、13 PASS + CAUGHT。Full Compilation1218.109秒＋post-fit26.779秒PASS，ALM29699/32070（93%）、setup/hold +0.629/+0.117ns，已实际下载并核对E9身份，蓝4零速校色/锁定预检4/4通过。画外蓝4实机INCOMPLETE：曾发现/锁定，60秒观察窗内未DOCK，主机STOP后零速；没有反向SEARCH，回扫物理效果未验证。E8蓝1/3/4已见目标停靠、蓝2分段证据与最后画外搜索NOT_FOUND分别保留；蓝5/6单独地面测试按用户要求取消。操作见[README.md](README.md)，证据见[修复验收记录](docs/REPAIR_RESULT.md)。

# Version history and validation / 版本与验证记录

This is the consolidated history of Member B and the later ECHO-7 B/C integration. Entries below run from the earlier
baseline to the latest work. Build identities, failed experiments and evidence
levels are kept separate. README.md is the maintained bilingual Chinese/English operation guide; OWNERS.md records individual-file responsibility and origin.

这是按开发先后整理的版本记录。MODEL、RTL_SIM、拟合、下载、相机实测和用户确认的
实体VGA分别记录；历史通过不能证明后续源码通过。课程要求、用户需求和设计选择也不混用。

**当前入口（2026-11-05）**：本页后半的“ECHO-7 整机修复与现场迭代”及末尾E5至E12记录本次
`dc1db23` 基线之后的工作。历史段落中的“最终”“不再下载”“静止 Member B 顶层”
以及当时的 R6 FAIL 只描述对应日期和源码，不能作为当前集成版本的结论。
此前已完成下载的`E7070008`正/负方向各433检查、88完整UART PASS；完整R6 PASS13项+CAUGHT、
270.641086秒、targetMet=true。Full Compilation1159.722秒及post-fit25.963秒PASS，
ALM29281/32070（91%）、setup/hold最差+1.021/+0.121ns；实际下载及E8读回通过。
已锁定蓝1起始的真实相机/J3/IR/UART落地接近、减速、末端对准与DOCKED完成一次，
首次观察ARM至DOCKED29.315066秒、J3329mm，DOCKED零速保持3.18423秒后正常收尾V1。
用户确认持续前进、偏转不明显；本次START来自主机一次命令，合成写入/心跳均0。
蓝2后续已有红2启动链记录及日志后前进/事后终态佐证，但缺完整移动遥测；蓝3已由
实体POWER完成真实移动DOCKED，15.726722秒/J3321mm；蓝4主机START也完成26.139371秒/
J3316mm的实际停靠，但保留抽动/偏右与17.1秒微调。用户取消蓝5/6独立地面测试，随后蓝4
画外起始搜索已以SCAN_BUDGET/NOT_FOUND结束；曾观察到目标但停车后未重锁，期间近障HOLD
与用户移障动作也如实保留。新E9只增加有限反向小步重确认，定向两sign各696检查/245UART
PASS；本版正式R6已独立PASS，274.530007秒、13 PASS + CAUGHT、targetMet=true。Full Compilation1218.109秒＋post-fit26.779秒已独立PASS且实际下载读回E9；画外蓝4实机INCOMPLETE，发现/锁定后反复对准、60秒观察窗无DOCK；主机STOP正常收尾，没有反向SEARCH，不能沿用E8实物PASS或声称回扫奏效。蓝5/6地面证据、重复性
等缺口保留，不作为追加扩测计划。
末端约25秒微调、重复性和左右位移差仍保留；E5/E7实测失败、E6时序失败未删除。

此前`E7070005`的方向控制回归在负生产参数及正泛型参数下各**269 PASS**，
固定25fps真实像素管线到UART回归12帧通过；正常长回波FAR分类、d页FAr和主机分类字段
已加入候选源码。首次完整R6 **FAIL，303.500928秒**：12项PASS，reader编译达到总期限，
mutant未运行；随后最终优化R6实际 **13 PASS + 1 CAUGHT，239.403059秒**，达到285秒目标。
Full Compilation **1173.143秒PASS**、post-fit **25.799秒PASS**，
ALM29507/32070、setup/hold最差+2.089/+0.116ns；E5下载及版本读回通过，当时设备
保持E5的VISION_ONLY/未ARM/零速；零速蓝1锁定及FAR分类已实测，三次物理满圈已确认并设13.6秒近似上限，误差与不稳定的起步单边前冲保留。新默认TURN_SIGN=-1只校正有效视觉转向，未证明具体接线根因。

此前已完成构建/下载的 `E7070004` 控制自检为 **254 PASS**，完整 R6 为 **12 PASS + CAUGHT，
219.556074 秒**；Full Compilation **1121.141秒PASS**、post-fit门检 **25.868秒PASS**，
22:31:50 AEDT新SOF下载及E7070004读回成功。真实红2重新选择、新锁定后ARM/ALIGN
板上链路已通过，用户确认实物启动，并最终澄清“蓝一脱离后就停车了”。
收口为VISION_ONLY/未ARM/左右逻辑零速，用户确认已停止；主机STOP的独立机械停车时刻未测，zeroSent只证明发送完成。
不借用E7070002/E7070003 的硬件动作结果。完整证据和待验收项目见
[修复验收记录](docs/REPAIR_RESULT.md)。操作入口为[中英双语README](README.md)；一页数据表发布位置为
[docs/ECHO7_Integrated_Datasheet.pdf](docs/ECHO7_Integrated_Datasheet.pdf)现为两页：产品操作指南＋正式R5指标；[独立R5数据表](docs/ECHO7_R5_Datasheet.pdf)严格一页并作为export的`--datasheet`参数。renderer从RTL header读取版本；R5项目目标及来源见[说明](docs/R5_TARGETS.md)和`tools/data/echo7_r5_targets.json`，E13三次实测/验收/claimed grade目前PENDING，不拼接旧版成绩。详细验证仍保留在指标记录与修复记录，各版证据保留实际范围。

## 2026-10-22 to 2026-10-23: same-group predecessor

The initial repository was paekinator/MTRX3700-Major-Project. The user confirmed
that Hajin and Jiaze Sun developed this preliminary code in the same group;
Hajin mainly handles Member A. Member B's confirmed SID is 540207680. The old
starter package was reference material, never a replacement for that repository.

Earlier AI-assisted work covered colour masks, display statistics, fixed-ROI
diagnostics and counterclockwise VGA presentation. The retained native camera
size is 320x240; display orientation is separate from recognition and B/C
coordinates. Earlier safety/chassis work belongs to the predecessor and is not
included in the current stationary Member B top. Early statements that the
formal Brief or Verilator were unavailable describe that time only.

## 2026-11-02: migrated repository and real-camera diagnosis

The migrated tree was reorganised around rtl/, quartus/, tests/, tools/ and
assets/. The layout commit was c67b34e; the subsequent user commit 63bc383 included
continuous-replay fixture work. Current work continues from actual HEAD
bfe9616139e88bc56c3f9798b21f49c044efc092 without reverting user changes. The inspected
remote is ErrorChen/MTRX3700_MajorProject_V2; no push or force-push was performed
by this continuation.

Real captures established these separate failure classes:

- Orange background entered the old red classifier. The production path moved
  to integer HSV comparisons rather than claiming that PDF RGB values were
  camera measurements. Hue/saturation gates remain fixed; calibration updates
  two brightness floors only.
- Aggregate per-colour boxes hid individual signs. Bounded connected components,
  per-object contours and typed labels replaced that coarse display.
- Oblique signs needed a measured quadrilateral and native anchor checks.
  White strokes and direction anchors now use different, explicitly versioned
  predicates. No digit is obtained from a sheet cell or candidate slot number.
- Several initial replay failures were test-data mistakes: shared expected.hex
  collisions and a positional vector index selecting a synthetic negative
  instead of a recorded frame. Named, source-checked fixtures replaced them.

The relocated 20-bench ModelSim suite eventually passed as one invocation
20261102T135055_875419Z_test. Earlier partial runs and failed aggregate invocations
were not relabelled PASS. Native preparation tests covered 131,072 division
inputs and 524,288 signed clipping boundaries. MODEL checks remained separate
from those executed HDL tests.

## 2026-11-03: compiler recovery before the external review

| Build or experiment | Actual result and consequence |
|---|---|
| 77744a75 | Fitter routing-congestion failure |
| d606e861 | MAP passed; full compile deliberately terminated; no fitted result |
| fd9950d9 | 3,600-second timeout; no completed fit/timing acceptance |
| 9c0e0297 | Post-map diagnosis found a 64.749 ns path and -45.030 ns slack; not a fitted result |
| e943678b | Pipelined preparation reduced that path to 11.526 ns; severe later routing congestion remained |
| Manual GUI run | Windows recorded Quartus20.1 quartus.exe/QtCore4.dll crash at01:45:43 Sydney; this did not establish a separate quartus_fit crash |
| ab41e932 | Isolated Quartus18.1 complete fit/timing passed; compile16m32s; worst setup+3.205 ns, hold+0.119 ns; programmed and read back schema2 |

The ab41e932 baseline used17,519 ALMs,347/397 M10K and29/87 DSP. Its new frame225
accepted red1/2 and blue1-5, rejected blue6, and had not yet calibrated. Later
real frame31285 did commit eight samples/config1 (red32/blue28), but candidate
overflow made that frame invalid. Therefore both "calibration never worked"
and "calibration completed, so recognition is stable" were incorrect claims.

Source-closure isolation, explicit tool paths, exact build/SOF hashes, full
warning retention and the post-fit clock/CDC gate were retained in the CLI.
Windows CRLF parsing initially made successful programming appear to fail;
the parser was fixed and a subsequent real program/readback passed. Old SOFs
were never promoted to products of failed builds.

## 2026-11-03: supplied review and its disposition

The supplied review checked HEAD bfe9616, source identity e1cd47da with41
dependencies. It executed Python3.12.14/NumPy2.3.5/Pillow12.3.0:99 tests with9
skips in266.328 seconds, not99 fully executed passes. Verilator was absent in
that review environment, so its R6 result was ENVIRONMENT_BLOCKED. It did not
run Quartus, ModelSim or the physical board. Its old-fit comparison found12
changed and2 added dependencies; old20-bench evidence had19 changed source/TB
hashes. The review's limitations were not treated as current local limitations.

The final Major Project Brief was supplied,7 pages, SHA256
`6c4311e60feb53cc1ec17c5d1f00c43baaf72788d73b166972d6b394eefa048c`.
It is retained at docs/Major_Project_Brief_2026.pdf. The three-person
proposal is a separate reference, not a rubric. The five lecture PDFs remain
under docs with their original filenames and unchanged bytes.

| Review finding | Implemented disposition |
|---|---|
| Busy JTAG calibration ACK could silently lose an arm pulse | Action-ready/BUSY rejection added; acceptance, start and terminal commit are distinct; real busy rejection subsequently tested |
| R6 oracle still selected colour1/reader3 | Production/model/vector/debug profiles unified; historical profiles remain explicit replay choices |
| Old calibration success followed by capacity overflow | Active and completed capacities measured independently; later shared16 design and real duplicate scene tested |
| Current fit/program did not match source | Each frozen source obtained its own build identity, SOF digest, readback and new acquisition |
| R6/R7/R8/R9 incomplete | Actual5.050 simulation/mutant detection, recorded-input RTL comparison, per-file SID provenance and physical algorithm comparison added |
| SW0/SW1 display evidence missing | RTL pixel/stream checks and user-reported four-mode physical confirmation obtained; not described as a monitor photograph |

The review's suggested SW2 and earlier SW9 comparison mapping were superseded
by the user: SW8 is the algorithm comparison; SW9 is complete processing/overlay
pause. Its request to show rejected SW0 slots was also superseded by recognised-
only compact panels. Microphone input remains explicitly deferred; no ordinary
UART or motion implementation was added.

## 2026-11-03: active-label and timing corrections, 5633257e

Build19b60d31/schema3 fitted and programmed. New frame343 recognised all eight
formal signs, but later90-frame observations included9 red active-capacity
overflows. A seven-sample calibration attempt failed without corrupting config1;
its busy-request rejection alone was not called successful calibration.

Real frame30507 needed nine temporary red labels although only two red and seven
blue outputs survived. The active12/output8 revision7eec0ba4 recovered this
geometry in MODEL/RTL but failed VGA setup at-0.291 ns. Exact reciprocal
arithmetic in b6e89ca6 removed the37-level constant-division path, but an artificial
Gray first-stage hold failure remained. A hold-only false-path experiment
discarded required skew checks and was rejected. The final constrained design
retained20 ns max/skew/net bounds, vendor-style asynchronous minimum delay and
explicit Meta-to-Sync checks.

The frozen5633257e source SHA256 was
`5633257ec6022612b9b023a46902db3fe74763cedffc4b331756c1c2e8c574d3`;
its SOF SHA256 was
`11b555f7b06d863a7c8172417cb72d32f951f29f2da663e13153901cbdebefca`.

| Layer | Executed result for5633257e |
|---|---|
| MODEL |136 host tests and11 counterfactual groups PASS |
| RTL_SIM |30 ModelSim benches PASS; clean Verilator5.050 R6 in62.375s, intended early-lock mutant CAUGHT |
| R7 | Recorded frame327 compared to model and normal/bbox RTL; both accepted8, so no perspective benefit demonstrated on that input |
| QUARTUS_FIT_TIMING |899.968s compile+20.437s gate;23,433 ALMs,347M10K,47DSP; setup/hold/recovery/removal minima+3.430/+0.118/+28.081/+0.412ns |
| CAMERA_HW calibration | Three8-sample commits; conservative board-time bounds557.651/622.279/554.597ms; busy arm explicitly rejected |
| CAMERA_HW first trials |90 current reports plus3 retained old-request drains;744/744 labels over93 observations; maximum43.183ms |
| VGA | Four SW0/SW1 combinations reported normal by user; no monitor photograph |

Later physical algorithm comparison on the same5633257e image found actual
failures: normal712/720 labels, bbox469/720; both strict runs FAIL. Normal
frame16493 exhausted active12. Three apparent old-request failures were host
assessment errors; their timestamp-based reassessment did not erase the real
overflow. The cancelled3fcf96d3 active15/output8 build was never programmed.
This old firmware used SW9 for the algorithm comparison, not pure-camera mode.

## 2026-11-03: shared16, automatic orientation and a9caa52f

User-added rotated duplicate blue1/2 created nine blue regions, exceeding the
old output8. An interim split16-per-colour buildaf566fa1 failed resource limits
(3,730LABs and36,364ALMs) and was not programmed. The final implementation has
one16-slot completed pool with explicit colour bits,15 temporary labels per
colour,335 invalid row cycles and a341-cycle core guard. Capacity exhaustion
invalidates a whole frame; it never silently drops a numbered sign.

Reader5 resolves the unique native direction anchor among four corner orders;
ID still comes from pixels. Public B/C v2 is unchanged; private schema7 has96
status words and16 shared marker records. SW0 panels are recognised-only,
blue#0-#7/red#A-#F plus uniquely owned BJ. SW8 is perspective versus bbox; SW9
pauses algorithms and removes all overlays while preserving camera/time/profile.

Frozen source SHA256:
`a9caa52ff9cb8ce06b69755ed3c398c1d9f23a7b7c727a82b13e5e9f0d90d44a`.
SOF SHA256:
`4be67b7f2c52e54a24bfbffed31e7ef9301f1605277bb74b136d8e2f5d8c679b`.
Build20261102T232355_017699Z_build and program20261102T234304_659966Z_program
used discovered DE-SoC[USB-1], FPGA chain index2, not an assumed HPS index.

| Layer | Executed result for a9caa52f |
|---|---|
| MODEL |222 tests, no skips,130.525s; clean727-file export222 tests131.311s |
| RTL_SIM |35-bench audited aggregate; original full run failed a missing negative-anchor fixture; exporter repaired,1,680 anchor ROIs plus all unchanged benches verified |
| R6 |Verilator5.050 production-core suite PASS81.344s; clean export PASS60.171s; intended mutant CAUGHT |
| QUARTUS_FIT_TIMING |17m36s compile+23s gate;72 timing/unconstrained checks PASS; setup/hold/recovery/removal+3.272/+0.119/+26.469/+0.409ns |
| Resources |Adjusted ALMs26,537/32,070; actual placement31,478/32,070(98%), all3,207LABs occupied;36,427 registers;347/397M10K;47/87DSP;1PLL |
| Warnings/CDC |114 warning occurrences reviewed; no unreviewed critical warning;63/63 synchroniser chains checked at four corners; numerical MTBF not assessed |

The initial new frame312 and30-frame trial recognised all eight blue signs but
missed red1's cropped top anchor:270/300 labels, overall FAIL, no calibration.
After the user adjusted the view, frame19645 recognised10/10 numbered signs
and paired BJ. Three real eight-sample calibrations committed config12/13/14;
busy requests were rejected in all three. Conservative attempt-to-commit bounds
were596.184/582.718/594.523ms, not precise internal red1-confirmation timestamps.

The user confirmed a9 SW0/SW1=00/10/01/11 as normal ("能正常显示"). This is
USER_REPORTED_PHYSICAL. RTL VGA previews are separately labelled, not photographs
of the physical monitor.

After a further small paper movement, frame30158 exposed a real limit: the
rotated blue2 anchor was only1x3 strong-white pixels. It was correctly rejected
by the current two-dimensional anchor rule. Its red1/reference pair had a3px
centre shift but a5px left-edge shift, exceeding the old fixed4px tolerance.
Raw sample purity itself passed (red252 samples, blue492); changing colour
thresholds would not fix that geometric condition.

The fixed-scene normal trial20261103T013437_754019Z_test used config18 and
three30-frame runs:300/300 labels each,900/900 total, no wrong IDs/overflow/new
drops, maximum46.322ms. SELECT1/2 gave30 expected zero-measurement ambiguous
reports; SELECT3-6 gave48 locked plus12 expected acquiring reports. The user
attested unchanged paper/camera/focus/lighting for the following comparison.
SW8 up/config19 produced298/300,298/300,299/300 (895/900), five rejects and zero
wrong IDs, maximum45.477ms; its strict development gate remains FAIL. Both modes
meet the declared95% numerical accuracy threshold, so this shows only a small
fixed-scene coverage difference, not a general perspective advantage.

Separate fresh frame37621 immediately after normal trials exposed another limit:
RUN3 horizontal support split a rotated blue1 into two components. Raw HSV and
causal cleanup alone retained one component; RUN3 cut its narrow side connections.
The90 sampled passes do not establish that every intervening frame passed.
The1x3 anchor and RUN3 split are different unresolved pixel-resolution failure
modes. Thin-anchor relaxation was explored and rejected because it introduced
false accepts; no success was fabricated from a known digit/position.

SW9 was physically tested with SW0/SW1 both on. The user confirmed
"确认只剩相机图像". Fresh raw frames45271/45502 advanced normally, config20->21,
all three raw-mode flags1, no candidates/observations/readiness, reasonFRAME_BAD,
same target request and committed colour floors. Down again produced frame47787,
config22 and the same tag46/blue3 locked; the sparse snapshots do not prove the
first two reacquisition cycles, which are covered in RTL.

The comparison helper's old fixed720 denominator was repaired to use verified
region/sample counts. Ten signs now correctly mean900 opportunities. Four new
negative/population cases and68 related tests passed; differing denominators
are rejected. This host-only change did not change the programmed FPGA.

## 2026-11-03: scale-aware pairing and documentation consolidation

The user requested removal of evidence/, member_b_review_pack/ and duplicate
docs Markdown, with a detailed bilingual README for future developers. The
maintained documents are now README.md, VERSION_README.md and OWNERS.md.
Reference PDFs remain under docs; formal marker artwork remains under
assets/markers. Required camera regression inputs and host-only truth annotations
move to tests/fixtures with byte hashes/provenance. Reproducible generated logs,
images, simulations and build databases belong in ignored build/.

Historical raw evidence directories are deliberately removed after extracting
their relevant findings here. This file records what was executed; it does not
pretend all old uncommitted raw logs remain distributable after removal. Prior
committed history remains in Git. Current-run originals remain in ignored build/.

The new pairing change replaces fixed endpoint tolerance with scale-aware
centre displacement, minimum overlap and existing width/height/gap ratios.
Unique red1 ownership and raw-RGB purity/stability checks stay intact. This is
configured-orientation bbox pairing, not an unlimited-angle calibration claim.
Its source, tests, fitted result and new board measurements are recorded below
only when executed; a9caa52f results above do not certify that new source.

### Executed checkpoint127d80b2: scale-aware calibration pairing

This checkpoint was completed before the later RUN2/publicv3 edits. Its exact
sourceSHA is127d80b2962cd3b1eb203e9270e1d569a90277437b0d2d7f63709e7d1329e2ab;
SOFSHA7618efef5201a3ddc9dd70fdf073d13045293f3431d5a5fdd51d68ff8dbb807a.
Build20261103T014610_881799Z_build passed full Quartus18.1 flow and timing.
Adjusted ALMs26528/32070; actual placed31581/32070 (98%); registers36651,
M10K347, DSP47, memory2790208bits. Worst setup/hold/recovery/removal slack was
2.588/0.102/27.511/0.397ns. All72 timing/constraint checks passed, with63
synchroniser chains.104 warning occurrences had no new unexplained signature;
ten previously reviewed32-to15bit truncation warnings disappeared after explicit
widths. Physical placement margin remained small and required another actual
fit for subsequent additions.

ModelSim's complete35-bench frozen suite20261103T014940_657181Z_test passed;
the R6 Verilator5.050 Bash entry20261103T014758_481494Z_verilator_course passed
in89.781s and caught the intended premature-lock mutant. The two targeted
calibration benches20261103T014519_152810Z_test passed310checks. An earlier
targeted aggregate014319 remained FAIL because its source changed mid-run,
even though its individual benches passed; it was not promoted to a green run.

Program20261103T021011_039452Z_program succeeded on DE-SoC[USB-1], FPGAindex2,
ID0x02D120DD; board buildId127d80b2/schema7 was read back. Fresh capture
20261103T021040_629684Z_capture, frame689/config1, recognised all10 numbered
markers plus uniqueBJ. Three real calibration attempts021125/021131/021136
committed versions2/3/4, each with8valid sample frames. Conservative observed
attempt-to-commit bounds were600946,605891,531185µs. Each busy-request rejection
test also confirmed the original attempt completed. Camera trial
20261103T021159_884118Z_test passed300/300 in each of three runs (900/900),
maximum capture-to-completion46313/46310/46309µs. These results certify
colourAlgorithm2/RUN3,reader5,public2/schema7, not the later unbuilt edits.

### Consolidation checks and subsequent RUN2/publicv3 development

The authorised cleanup removed1705 files totalling92.7MiB after a SHA inventory
at build/member_b/document_cleanup_inventory.json. Required regression inputs
were reduced to15real PNGs and their profiles/truth/provenance,28files about865KB
under tests/fixtures/camera. Seven reference PDFs were retained byte-for-byte;
their final location is docs/ directly. Formal single-page marker artwork stays
in assets/markers. No Git history or user database was removed. Later Git HEAD
was observed at d1c29be (user commit,2026-11-03T13:46:29+11:00); source hashes,
not an assumption about an earlier HEAD, bind each test/build.

Post-migration MODEL run20261103T015637_094102Z_test passed239tests with no skips.
An earlier isolated export run retained three scratch-directory setup failures;
the fixed BCTL/submission follow-up015326 passed9tests. Portable repository
checks now work in an exported tree without.git, using a temporary isolated Git
directory and real ignore semantics; six new tests and an actual no-Git export
passed021140_repository_check. The explicit datasheet sidecar/source hash is
required before a generated PDF can enter a submission ZIP.

RUN2 was introduced specifically for the observed frame37621 split, retaining
the filter's two-token delay and flush schedule. ColourAlgorithm3 uses the same
HSV2 gate but keeps runs of at least2pixels; historical colour2 remains RUN3.
Across15real images/32profiles, model accepted counts were267(RUN3),269(RUN2),
271(no horizontal filter), with no existing accepted ID lost and no overflow.
RUN2 reconnected the measured two-pixel side bridges. Peak red/blue activity
increased from9/8 to13/9; synthetic sixteen width2noise bars can now overflow
and correctly invalidate a frame.410synthetic cases preserved295 accepts,
236 explicit negatives had zero false accepts, and334known expectations had
zero mismatch. The real1×3 anchor remains rejected; no direction was guessed.
The actual dual-RUN2/RUN3 RTL bench021935 passed2841rows,909120pixels and
243local patterns. Related91host tests passed with resultSHA
f7089e5913dc6625bb3abfed5351ac850bab98c98b03d4ba3cd30a185a3efa40.

The user's next interface request exposed that publicv2 SELECT could only track
blue bays and offered no public marker inventory/location query. Publicv3 adds
typed identities (blue bay, red function, uniqueBJ), LIST/GET alongside the same
CLEAR/SELECT request channel, and an independent query response stream. Query
snapshots use three small synchronous descriptor banks, not a second colour
frame buffer. All positions still derive from recognised pixels and retain
native frame/time/config metadata. GET returns all same-type/digit positions;
tracking refuses ambiguous duplicates. Private schema8 and QRP3 transport,
host commands/client, consumers and tests are upgraded together. The sole
normative protocol is README §7–8 and perception_pkg.sv.

During implementation, targeted run024944 passed CDC, collision, calibration
and pause benches individually but its aggregate remained FAIL because the
query-store source changed during execution. Final frozen-source evidence must
be recorded separately; no partial run certifies a later binary.

### Current-source completion record

Checkpointca5dc67d completed publicv3/private8 and colourAlgorithm3/RUN2,
reader5. SourceSHAca5dc67d6d53b412ddaf23254194d0c16e5bf16107c517609f8d7c4b91211de9;
SOFSHA93e52e763b1de1582aebf7a92e7d7e207c0f9dafd9b2ea47d4e0afbf218b2217.
MODEL20261103T030213_630482Z_test passed283tests plus counterfactual groups.
The frozen37-bench ModelSim suite030213_680753 passed in21min34s, with no
source drift. R6 clean Verilator5.050 passed six production/module benches and
caught the deliberate early-lock mutant in108.125s (025433_037716).
Query-store standalone validation passed1313checks/43queries/107packets;
the new core query test passed17checks/13packets using explicit reader-result
injection, not camera pixels. A VGA fixture that still sent schema7 while
expecting a schema8 BJ label failed025428, then was corrected to use current
package constants and passed; production VGA logic did not change.

Quartus build025754_918086 passed in18min08s plus23.703s extra timing audit.
The correct top/device fitted: adjustedALM27542/32070 (86%), physical placement
32070/32070, with5380ALMs estimated recoverable by dense packing; this is not
an out-of-capacity result. Registers37140,349M10K,47DSP,2793072memory bits.
Query descriptors mapped to exactly2M10Ks as48×49 simple dual-port synchronous
RAM (unused64-bit padding optimised away), not an array of reset registers.
Worst four-corner setup/hold/recovery/removal slack2.678/0.118/25.222/0.477ns;
all72timing/constraint checks and four-corner63/63synchroniser coverage passed.
Request CDC covers24bits; resultToCamera covers1601endpoints; display796 is
unchanged. Every changed endpoint is within intended protocol/debug fields.
Independent warning/resource review found no new unexplained warnings or
pending exceptions. Full compile reported100warnings, all retained/reviewed.
Numeric MTBF remains NOT_ASSESSED. The debug frozen-bank clear adds noticeable
logic; a read-masking optimisation was analysed but deliberately not applied
to this passing source.

Program031717_832062 passed on the same uniquely discovered DE-SoC[USB-1]
FPGAindex2 (0x02D120DD), with actual ca5dc67d/schema8/public3 readback.
Fresh frame270 in031731_104872_capture passed CRC/same-frame/model comparison,
but **did not pass full-sheet recognition**: actual SW8 was1 (bbox bypass),
SW9 was0, config1, red1 and a top blue sign were clipped. Only blue5 was
accepted in that frame; calibrated0/BJfalse. This image is different from the
earlier fixed-scene truth and must not be scored against frame30158's regions.
The user was asked to return SW8/SW9 down and bring the full signs into view.

Real query smoke031934_markers returned the actual blue5 observation. Subsequent
BLUE_BAY/5 SELECT, GETblue5 and GETBJ passed public transaction checks: tracking
tag2 stayed unchanged through query tags3/4, blue5 remained locked, and missing
BJ produced a sole zero-measurement QUERY_NOT_FOUND packet. Details are in
build/member_b/ca5dc67d_initial_query_smoke.json. This is partial-scene interface
evidence, not a ten-sign, red-function, calibration or arbitrary-lighting pass.
R7 recorded-frame270 normal and bypass RTL/model comparison032112_857697 passed.
Normal-model investigation separately exposed an adjacent-card anchor ownership
failure: blue2/3/4 can include the next sign's white anchor and reject ambiguity.
Its cause is separate from the clipped red1, actual SW8 setting and prior1×3
anchor limit; no physical normal-mode success was claimed for this new pose.

README §7.10 was expanded after the user requested clearer parameters: every
command, valid type/digit combinations, GET=3 versus REFERENCE=3 versus F=15,
transaction tags, target substitutions, return codes, coordinates and executable
Python imports are explained in both languages. Independent implementation
review corrected readiness semantics, report-reason priority, query preservation
of tracking and the absence of an implemented run-time default-restore command.

### 2026-11-03, reader6 and command explanation follow-up

The source now identifies readerAlgorithm6, while retaining publicv3/schema8
and colourAlgorithm3. A white anchor component must have its exact doubled
bbox centre within its original measured candidate bbox. Full containment
was rejected experimentally because it lost17 previously accepted real
observations and four synthetic ones. The centre rule kept every previous
accepted candidate's bbox/type/digit/quality/orientation in33recorded-image
profiles:272 to274 accepts, restoring only frame270's blue3/4. These are
replays of preserved camera images, not33new independent acquisitions.
Frame270's blue2 still rejects UNKNOWN_PATTERN/ABDG; its actual E stroke
exists, but the estimated quad puts most samples outside it. No digit or
orientation is guessed. The clipped red1 remains a separate physical-input
blocker. Evidence: build/member_b/reader6/real_matrix.json.

The native RTL latches the34-bit owner bbox with its quad and compares10-bit
X/9-bit Y doubled centres before rounding. Targeted RTL passed18independent
edge/half-pixel/ownership cases,42anchor ROIs,131072division checks and
524288clipping checks. Three reader vectors (real frame270 and two explicit
own/neighbour-anchor counterfactuals) passed8960sample-coordinate comparisons.
Frame270's reader-only latency was282418cycles/5.648ms; this is not capture
or end-to-end latency. Evidence: reader6_targeted/result.json.

Versioned exports use MODEL_8, PROJECTIVE_VECTORS_5 and NATIVE_ANCHOR_VECTORS_2
(24words, original bbox appended). Historical reader5 keeps its original
models/formats and full-reader RTL replay explicitly sets
ENFORCE_OWNER_BOUNDS=0; reader6 uses1. Current shared-pool RTL does not pretend
to reproduce earlier/split-pool architectures. Host decoding fails closed
for unsupported combinations.145related HOST tests passed, including reader6
CLI propagation, unchanged historical5 and interface-profile drift rejection
(reader6_host_validation/result.json).

The previously reviewed QRP3 resource optimisation is now implemented: eight
packet words are stored, and the unused tail is masked to zero at the32-bit
read port. It avoids clearing88stored words on every query response. Debug
tests explicitly read every tail word after each of16packets and verify that
a subsequent status freeze restores all96words. Both debug/link benches passed
034008_295970. This changes no public or private wire format.

Source9070d1ed (SHA9070d1ed03edaa301cb43f823e211fed01cbc865a463f2d5fcb9ec35ed9a5193)
is under final37-bench simulation and Quartus build034215_716773. Full MODEL
034125_979536 passed310tests in268.007s, plus counterfactual groups; R6 clean
Verilator5.050/Bash034126_392190 passed six benches and caught the intended
early-lock mutation in112.172s. These are not fitting or board claims.

README7.10 now explains every command, all four request fields, valid selectors,
GET versus SELECT, JSON return interpretation and parameter substitutions.
Independent review checked seven real CLI help invocations and Python/RTL
signatures (reader6_host_validation/readme_7_10_review.json); all passed.

The completed checkpoint is recorded below. Microphone input remains deferred
by the user. Human ownership/sign-off, numeric physical operating ranges,
remaining relevant AI conversation exports, new occlusion/lighting tests and
whole-team integration remain separate responsibilities.

### 2026-11-03, reader6 completed board and interface validation

Source9070d1ed completed all37 ModelSim benches with no source drift
(034125_931495). Build034215_716773 passed in1105.766s plus26.406s explicit
timing audit:27071/32070 adjusted ALMs,37253 registers,349/397 M10K,
47/87 DSP and2793072 memory bits. Worst accepted setup/hold/recovery/removal
slack was2.601/0.107/25.034/0.442ns. All72 timing checks and63/63 synchroniser
chains at each of four corners passed; quantitative MTBF is NOT_ASSESSED.
The100 normalised warnings matched the previous reviewed checkpoint; none
were newly unexplained. Query storage remained two M10K,48×49 useful bits.
The query-tail read mask reduced memberBDebug total ALUT2287 to1005.

SOF SHA256 is725882cfe7bf547acdb3da3c3a5e7a5066d19bf181fca0c904d022dc3042da6d.
Program040143_422680 selected the discovered DE-SoC USB-1 FPGA, verified the
same target identity and read back9070d1ed/public3/schema8. Capture040119
correctly failed before programming because the new build manifest and old
board differed; that failure was retained. Fresh capture040200_186255 produced
real frame364,config1,ten accepted printed digits and one uniquely paired BJ.
Its PNG, hash, origin, profile and independently reviewed host-only regions
are retained under tests/fixtures/camera/frame364. Paper edges touch the image;
this is not a claim that every physical sheet edge is visible. R7 replay
040546_827101 compared these actual pixels/profile with both RTL modes.

Three real recalibrations040344_444187,040348_656946 and040353_069673 passed
eight-sample commits and busy-request rejection, advancing config2/3/4.
Board-time poll upper bounds were580208,604969 and532525us; these are
conservative command-to-observed-completion bounds, not exact red1 onset
latencies. Last hardware sampling recorded252 red/504 blue pixels; a later
same-image model measurement of288/492 uses a different ROI/time and is
explicitly separate. Raw RGB validation does not imply AWB/AEC lock.

The real publicv3 interface test040433_321702 passed LIST, typed GET,
red1/red2/BJ SELECT, blue1/2 duplicate ambiguity, CLEAR and unaffected tracking
requests during queries. It held a query under backpressure while camera
frames continued and a genuine calibration committed config4 to5: held
payload/time/config remained unchanged, then a new query returned the new
configuration. All issued requests, responses and profile identities are
recorded by tools/validate_member_c_interface.py.

Normal hardware trials040656_032083 scored900/900, then SW8 bypass trials
041414_952228 also scored900/900, both three trials of30 distinct fresh frames
with ten signs. The first comparison was INVALID_COMPARISON because the host
runner changed. Normal trials were therefore repeated using the identical
frozen-checkpoint wrapper:041845_157073 scored900/900, zero wrong IDs/misses/
outside-region results. reader6_sw8_comparison_repeated.json is valid; both
modes pass. This scene demonstrates the physical bypass mechanism but does
not demonstrate an accuracy advantage or necessity for the normal algorithm.
These are sampled frames, not a claim about every intervening frame.

The user confirmed all four SW0/SW1 combinations and BJ, then confirmed that
SW0=SW1=SW9=1 shows only the camera. The later actual readback already had
SW9 down, and blue3 requestTag75 was locked again at frame44819/config9.
reader6_raw_user_confirmation.json distinguishes USER_REPORTED_PHYSICAL raw
display from the hardware-confirmed restoration; no raw-up status snapshot
was captured in this transition. No physical switch was simulated by the PC.

### 2026-11-03, reader7 main-colour ownership and overload investigation

Source7408a02d1009327f790bf246331e7f718f4671ba9f3998233ce07374ffb51ef9
keeps public3/schema8/colour3 and identifies reader7. Frame270's blue2 contained
a real three-pixel E stroke, but raw pixels belonging to the neighbouring blue4
pulled its estimated lower corner from[244,61] to[244,72]. Taking supports from
the unique largest four-connected raw-colour component restores seven of
seven E samples instead of one of seven. The component bbox must match all
four original candidate edges; ties, mixed bounds or active-label overflow
reject. Area is never used to assign a number. SW8 skips this additional scan.

mainColourSupportReader uses eight active labels,320×4 synchronous line RAM
and128×28 synchronous support RAM. Targeted RTL passed565 cases/13689 checks,
including512 small topologies,27 external vectors, merge/retirement/ties,
overflow, held inputs and reset. A union-support-loss mutant was caught by
the intended support assertion; ModelSim's raw exit0 was correctly converted
to failure by the wrapper. Full-reader integration passed normal/bypass and
historical reader6; maximum measured reader-only processing on these vectors
was1319652 cycles/26.393ms, excluding acquisition. Historical algorithms remain
explicit and are not silently reinterpreted.

MODEL042234_461679 passed341 tests plus counterfactual groups. Separately,
410 synthetic cases preserved295 prior accepts and had zero false accepts
among236 negatives. Across33 recorded-image profiles accepts rose274 to275,
with no lost IDs/orientations/bboxes. The strict all-field equality comparison
remains FAIL because an existing blue3 quality increased192 to255; the separate
non-regression assessment explicitly permits that improvement. These are
recorded-camera replays, not new board captures.

R6 run042119_525858 failed on the old continuous-frame test at frame3. An
independent ModelSim trace confirmed that its17.1609ms source period, which
omitted skipped sensor-row time, delivered frame3 at34.323470ms while the two
banks were READING and READY. The core correctly rejected the entire incoming
frame; at51.483070ms it published frame3 as bad/resourceDrop with zero matches.
The previous assertion incorrectly required every such frame to be observed.
The in-progress larger simulation042108_403104 was explicitly INTERRUPTED,
not reported as passing. Verification now separates a free-running40ms source
representing the measured camera from the original17.1609ms overload, retaining
drop/ownership/backpressure checks and requiring fresh three-frame relock after
recovery. No ready feedback is added to the simulated camera.

Build042031_633519 passed full compilation and the explicit four-corner timing
gate at04:40:52UTC. Source7408a02d binds SOF SHA256
0ebb6a4849cd1f5e9499cca80929ee198682cc3f287e72ea1defc11663c23a39.
Fitting used27810 adjusted ALM,38002 registers,351 M10K and47 DSP. The new
supportMemory128×28 and lineLabels320×4 each occupy one physical M10K, rather
than a register array. Full compile took1190s; fitter itself10min36s, with
placement and routing successful. This was active computation, not the earlier
memory-starved stalled build. All100 warnings match the previous reviewed
normalised set; full timing details remain in the source-bound result.

The detailed placement table displays32071/32070 ALMs while the root entity
table reports32069.9. Both values are retained in main_colour_resource_review;
local Quartus18.1 help documents proportional attribution of shared ALMs across
entities but does not establish the exact integer summary rounding formula.
FIT succeeded without an overuse error. This accounting difference must not
be presented as one extra physical ALM or hidden as spare placement headroom.

The revised cadence tests passed four independent ModelSim modes: continuous
40ms,17.1609ms overload followed directly by40ms recovery, truncated-frame
recovery, and protocol collision injection. The overload produced exactly two
whole-frame input drops and two stale-result rejections; the next request's
three new frames locked only on the third. Dropped frames wrote zero pixels;
admitted frames wrote exactly76800 sequential addresses. Stalled reports did
not change. Evidence:core_cadence_validation/summary.json. The production RTL
did not require a scheduling change.

Course R6 rerun043842_301612 passed all eight module/system benches and caught
the deliberately early-lock tracker mutation in228.031s, below the300s rule.
It includes both normal and overload system tests. Nine host runner tests
separately passed and guard against silently dropping either scenario. The
39-bench ModelSim development regression043535_957637 is still running;
programming and fresh reader7 camera evidence remain pending at this entry.

### 2026-11-03, reader7 completed checkpoint and two photographed poses

The previously pending development regression043535_957637 completed at
05:10:31UTC with39/39 ModelSim benches passing. Together with R6
043842_301612 (eight system/module benches plus the rejected early-lock
mutation), this completes the recorded simulation checkpoint for source
7408a02d1009327f790bf246331e7f718f4671ba9f3998233ce07374ffb51ef9.
Build042031_633519 passed fitting and the explicit final four-corner timing
gate; its SOF SHA256 is
0ebb6a4849cd1f5e9499cca80929ee198682cc3f287e72ea1defc11663c23a39.
Program044313_012680 succeeded on the discovered DE-SoC USB-1 Cyclone V
target and verified build7408a02d/public3/schema8. This is reader7 board
evidence; later reader8 model defaults do not relabel it.

Fresh capture044324_762472 produced frame241. Its two extra blue1/2 signs
had moved approximately30 pixels relative to frame364, so the earlier frozen
frame364 predictions are retained with an explicit scene-condition mismatch.
They are not retrospectively claimed as predictions of this changed pose.
Three recalibrations044349_203668,044421_302088 and044426_305022 passed;
the observed board-time completion bounds were592011,580674 and600539us.
The publicv3 interface test044436_346297 passed41 checks. R7
044627_573160 passed both RTL modes on the exact frame241 capture.

The corrected, independently labelled frame241 truth regions were used by
normal run044951_489860:900/900 printed digits, zero wrong IDs,90 current
reports and99 distinct observations including request transitions. Its maximum
board capture-to-completion latency was65.417ms. The preceding truth-v1
run044701_227993 remains retained; the v2 correction removed an overlapping
score-region edge and did not retrospectively replace that run's inputs.
The matched SW8 bypass run045104_494342 also scored900/900, with91 total
observations and45.580ms maximum latency. reader7_sw8_comparison.json is
COMPARISON_VALID under the user's unchanged-scene attestation. All four
SW0/SW1 combinations were confirmed physically by the user. Neither these
scores nor that confirmation proves an accuracy benefit from perspective
recovery or substitutes for a reader7 SW9-up hardware snapshot.

The subsequent physically rotated pose is a separate eight-sign scene,
retained as frame15078. Normal run045611_428051 scored717/720, with three
missing printed observations and no wrong IDs. Its strict hardware result is
FAIL: four of95 retained observations failed, including one unreliable or
unlocked target report. Maximum latency was58.494ms. Matched bypass
045949_085041 scored720/720 and passed, with44.143ms maximum latency.
reader7_rotated_sw8_comparison.json is a valid comparison containing that
normal-mode failure; it is not converted into a pass because aggregate
recognition exceeds95%. These results do not demonstrate an R9 digit benefit
for the normal algorithm. A later bounded search saved30 distinct fresh
images, frames32136..38058, all with blue6 accepted and no frame/overflow
failure. rotated_failure_capture/result.json correctly records
NO_FAILURE_CAPTURED_IN_BOUNDED_RUN. It neither erases the earlier failures nor
supplies a captured blue6 failure image for a claimed repair.

### 2026-11-03, reader8 projective calibration development, not yet board evidence

The rotated frame15078 exposed a separate calibration limitation. Red1's
bbox[117,1,176,87] and its blue reference bbox[115,81,170,105] have native
axis gap-7 pixels even though the strip is correctly below the slanted card.
The old axis-aligned blue inset also includes white/background pixels:
495 raw samples have B minimum57 and other-channel maximum174, so purity
fails independently of the pairing decision. Merely loosening the gap test
cannot provide valid calibration. The stored diagnosis remains under
rotated_calibration_15078; it is recorded-pixel analysis, not a new commit.

Reader8 preserves reader7 digit, anchor, ownership, white and colour3 rules.
It adds same-frame measured quads for calibration, allowing a blue strip with
a four-pixel bbox minimum to publish geometry while retaining the numbered
card's24-pixel edge and400-pixel area gates. SW8 bypass publishes no such
quads. Default host MODEL/export metadata now names reader8; explicit
readers1..7 retain their historical behaviour and version IDs. Nine exported
frame15078 digit/map/mask/candidate files were byte-identical between7 and8.
The thin-blue synthetic test remains UNKNOWN and never becomes a bay.

The new maintained geometry oracle uses forward homographies, canonical
scale320 and exact floor-Q4 coordinates, including negatives. It compares the
formal strip projection with the actual component under a scale-based corner
budget, edge ratios and forward half-plane bounds, requires unique cyclic
matching, and samples each object's own inset polygon. Blue sampling order
follows the winning cyclic correspondence. No inverse matrix or new RGB frame
buffer is required by this design. The initial nearest-Q4 experiment remains
separate from the new floor-Q4 results.

The floor model preserved30/30 old valid real profiles, produced31 raw-pure
pairs, rejected all215 neighbouring bays even when their accepted flags were
removed, and rejected six wrong-reference geometries. Of540 controlled
rotation/perspective/scale geometries,536 passed; four small projected-gap
collapse cases remain conservative rejections. Five raw-colour contamination
cases and the15-sample negative were rejected. Model sampling of frame15078
suggests blue floor28 instead of33. In the RGB565 input representation there
is no blue-channel level between24 and33, so this floor change alone changes
no pixel classification; it is not a digit-recovery claim.

Targeted host/model validation passed46 tests, and14 focused historical
tests passed after making the current8 and historical7 defaults explicit.
The817-record geometry vectors retain valid, invalid, rounded-degenerate,
extrapolation and cyclic-order cases. RTL integration, complete current-source
regression, fitting/timing, programming and new calibration-camera validation
are still separate gates at this entry. Reader7's fitted/programmed evidence
must not be presented as reader8 completion. Microphone input remains deferred.

### 3 November 2026, 05:49–06:08 UTC — configuration fix, full-core replay and fit failure

The complete MODEL run `20261103T054332_443689Z_test` passed355 tests and the
counterfactual entry. Its preceding failures concerned stale default-version
assertions and a missing datasheet description; those failures remain recorded.

An independent RTL probe found that the eighth old-version calibration sample
could coincide with a mode/configuration change and later request a commit.
`reader8_geometry_port_validation/config_boundary_result.json` retains the FAIL.
The repair binds a complete attempt to `attemptCfgVersion`, rejects changed
versions through WAIT/COLLECT/VALIDATE/COMMIT and immediately gates collection
and commit. An acknowledged commit is final. Pending SW8/orientation changes
also take priority over an old-profile commit at the core SOF boundary.
Updated interaction tests and the original counterexample passed ModelSim;
core calibration passed318 checks, including3px versus49-Q4 movement,
unchanged old thresholds and no false acknowledgement on mode switches.
See `reader8_geometry_port_validation/receipt.json` for source/log hashes.

`perception_calibration/perceptionCalibration_tb_verilator/result.json` passed
52 frames derived from the single actual frame15078:116 checks,18 raw-RGB
sampling frames, three terminal events, one SOP commit and SELECT1–6 each
locking only on its third new simulated observation. Permission revocation
and configuration changes retained the old48/20 profile; a fresh eight-frame
window committed37/28. Each sample contained177 red/272 blue pixels using
the reset/default-derived geometry. Earlier177/274 model samples used a
different profile. CSV files preserve samples, events and reports. This is
RTL_SIM of repeated recorded pixels, not52 independent camera acquisitions.

Source645102d6 SHA256 is
`645102d67d5e166d4298fb8ca5d79464a5a0ddc82524fcad05c13b905b6d7a9e`.
Actual R6 passed eight benches plus the caught early-lock mutant in255.766s
(`20261103T060008_784610Z_verilator_course`). An earlier loaded-machine run
exceeded300s and remains FAIL. The runner now reuses an identically compiled
core only within the current clean run, with binary/source/tool hashes and
separate continuous/overload simulation logs;13 HOST tests cover this change.
It never loads a previous run's binary or relaxes the300s gate.

Full build `20261103T055358_022378Z_build` FAILED placement preparation:
Error170012 requires3374 LABs, but the5CSEMA5 has3207. The incomplete-fit
estimate is33142 ALMs (103%),39589 registers and57 DSPs. These are not
completed timing/placement results. MAP correctly inferred16×88 geometry
storage as M10K. No SOF from this attempt was programmed. The earlier
e6a60680 build was interrupted for the proved configuration bug. Interrupted
full ModelSim runs retain partial results and interruption records, never a
full-suite PASS. VGA storage/control resource reduction is in progress; the
board still runs the successful7408a02d checkpoint.

Fresh frame45625 (`20261103T055719_167964Z_capture`) passed CRC, same-frame
and glyph checks with no candidate overflow, but rejected blue6 with reason4.
Its strict-white anchor is a closed1×3 component with three pixels; only the
two-column requirement fails. Adjacent unsaturated edge pixels fall below the
strong-white threshold. This differs from the earlier unrecorded uncertain
stroke/split refusals. Exact PNG/profile: `tests/fixtures/camera/frame45625/`.
A conservative strong-seed/weak-support model restores this example, but is
not yet a production RTL or camera fix. No global white threshold was lowered.

中文记录：真实图回放已验证许可撤销、版本切换拒旧、八帧采样、原子提交和
蓝1–6三帧锁定；R6实际入口通过，但拟合因LAB超限失败，尚未下载。
新实拍已保存蓝6锚点只剩一列的拒识反例。资源优化与锚点修复分别验证，
MODEL、RTL_SIM、失败拟合和真实相机证据不能相互替代。

### 3 November 2026, 06:09–06:33 UTC — generic anchor recovery and resource reuse

Fresh recorded frame63647 (`20261103T060920_641543Z_capture`) retains another
reader7 anchor refusal. Its full blue6 box remains[264,176,296,236]; an extra
inner blue island is not the earlier unrecorded split-card failure. Both
frame45625 and63647 are preserved with original pixels/profile in the small
camera fixtures. No historical result has been relabelled as reader9.

Reader9 adds one general rule, shared by every red/blue digit and rotation.
All four strict-anchor hypotheses run first. Zero strict matches, no hazard
and exactly one closed thin strong seed permit one additional scan through
the existing native component engine. Its complete weak support must retain
every seed pixel, contain no foreign strong pixels and pass the original
closure, size, area and ownership conditions. True strong count is retained;
fallback quality is capped at192. SW8 and historical reader profiles keep
strict behaviour. There is no blue6, slot or scene-position branch.

Final native source SHA256 is
`943f3330ac0550168c76ad30b8d5a90abcc8f27cdae4768ffdd4a0eae7f8348c`.
Actual component RTL passed73 cases/1193 checks, including27 supports,
14 refusals, two overflows and one ambiguity. Strict old/new cycle comparison
passed1868 ROIs and7,288,257 cycles, including overflow/ambiguity. A deliberate
foreign-strong mutant failed as required; the checked runner propagated a
nonzero result despite ModelSim's raw `$fatal` exit behaviour. Independent MAP
estimated1434→1589 ALMs,2228→2492 ALUTs,1196→1390 registers, with1280 RAM bits
and10 DSPs unchanged. These are isolated synthesis estimates, not full fitting.
Receipt: `build/member_b/native_anchor9/review.json`.

MODEL preserved all old decisions across33 recorded profiles/330 ROIs and
410 synthetic cases/577 ROIs: zero lost/changed IDs, changed qualities or
negative false accepts. Eleven added host tests cover32 formal type/digit/
quarter-turn combinations and explicit counterexamples. The current-source
targeted actual ModelSim run `20261103T062653_461164Z_test` passed11 normal and
11 bypass cases, including both real failures, strict-priority/multiple-seed/
foreign-bridge negatives, four type/rotation examples and unknown/deleted
anchors. Normal mode recovered the two real blue6 anchors; this is RTL_SIM
using recorded pixels, not new CAMERA_HW. Full43-bench regression is separate.

VGA diagnostic work/published records now use a three-bank synchronous M10K
store; displayed records remain stable during serial loading and SOP
preemption. Actual old/new pixel and handshake equivalence passed3,944,178
pixels. The enhanced bench exercised2214 writes,46 load preemptions and17
cycles with all three banks owned. Independent same-settings MAP estimated
9908→7332 ALMs,9747→6189 ALUTs,6517→4016 registers; it inferred96×77bits of
M10K, with20 DSPs unchanged. Pipeline/SW9/arithmetic tests passed in
`20261103T061918_135877Z_test`. No display function was removed to save logic.

Current full build `20261103T062826_889919Z_build` uses source
`c63c9edbbd669744c7dee86f060352bf48ff9557bb0989f8084091860e4691d2`.
At this entry it is RUNNING, with the old7408a02d still programmed. A successful
isolated MAP or pixel replay is not evidence of final fit, timing or VGA
hardware. The complete flow, new SOF identity and fresh camera tests remain
required. The maintained inventory now covers230 files and43 RTL benches;
structural validation passed and human R8 sign-off remains pending.

中文记录：按用户要求采用通用判断规则，分时复用原扫描硬件；蓝6实拍只是
反例输入，不是专用识别分支。旧严格路径逐周期等价通过，薄锚点补查及拒识
反例实跑通过。VGA面板改用同步RAM，新旧逐像素一致，独立综合减少逻辑。
完整新工程仍在构建，不能将这些结果称为已经下载或相机验收通过。

### 3 November 2026 — final scope freeze and remaining blue6 failure

The user requested that blue6 instability be deferred and that work close
after one final programme. Production source remainsc63c9edb; no threshold
or recognition changes were made in response to the following new frame.
Fresh frame30321 (`20261103T063047_128847Z_capture`) still came from7408a02d.
Its blue6 raw HSV region is already fragmented:26 components, largest410px
ending aty210; cleanup leaves331px ending aty207. Of1459 hue/saturation-blue
pixels,881 fail the current value33 gate;501 lower-half pixels have expanded
blue24. A28 floor produces the same quantised mask. Diagnostic20/24 models
recover the sign, but these are not calibration or hardware acceptance.
Lighting/AGC/AWB/pose causes remain unisolated. The image is retained as
`tests/fixtures/camera/frame30321/`; its PNG SHA256 is
`4516b99ec2508b5ae170526397e9a7dff1836633b0ac8401395cb1b0558abb93`.
This upstream failure is separate from the two recovered thin-anchor inputs.

Final MODEL `20261103T063253_699527Z_test` passed370 tests in273.388s plus the
independent counterfactual command. It used an explicit900s host-run timeout;
the first default300s timeout remains FAIL. The course R6 budget was not
changed: run062658 passed its first seven benches but hit300s during the
last compilation, so its final bench/mutant did not execute and the aggregate
remains FAIL. Historical source645102d6's255.766s R6 PASS is not a current
source PASS. The broad current43-bench ModelSim run062727 was intentionally
interrupted after eight completed benches to honour the close-out scope;
its partial results/interruption record are retained. Current targeted
normal/bypass/component/equivalence proofs remain individually valid. The
existing52-frame changed-core test is being completed using Verilator,
separately from the course300s claim.

The pre-programme prediction was frozen at06:34:11UTC in
`reader9_predictions/predictions.json`, SHA256
`a5ed8fd0bbb688e2e4b2c6ce2d920347c2bfa3f9ebeb233ccc157fe09062ba24`.
It records design expectations, not measurements. The separate condition
assessment flags frame30321's slight pose/photometric change. No final90-frame
trial, SW8 advantage or new physical VGA confirmation is implied by a single
close-out capture. Those checks are deferred rather than silently passed.

中文记录：用户要求蓝6问题暂缓、最后一次下载后收口，源码冻结。
370项MODEL通过；R6本轮因300秒总限时失败，不能引用旧版本成功代替。
完整43项ModelSim按收口范围中止并保留已完成八项，针对性仿真单独计证。
本次仅完成最终构建、下载和新帧必要核验，不再安排三轮/开关对照实验。

The current-source52-frame Verilator integration subsequently PASSED:
19.219s compile,258.016s simulation,116 checks,18 accepted raw-sample frames,
three expected events and one atomic commit. All SELECT1–6 lock sequences
were0,0,1 on their three new simulated observations. Source hashes matched
thec63c9edb build throughout. Exact result SHA256 is
`b34358caeb4d45dc1e2cf49bba5d992455fabe15648f21a12e6efe1a61c92209`,
at `reader9_calibration/perceptionCalibration_tb_verilator/result.json`.
CSV samples/events/reports and evidence.json preserve each transition.
This repeats recorded frame15078 with report-paced input; it is neither
52 independent camera acquisitions nor a course R6 aggregate-budget PASS.

### 3 November 2026, 06:50 UTC — final programme and close-out

**Final source:**
`c63c9edbbd669744c7dee86f060352bf48ff9557bb0989f8084091860e4691d2`.
**Final SOF SHA256:**
`3e4f572055f63c02436608623a7994fbf5d840cccc13ba7b8e5c11bca2524d1d`.
Build `20261103T062826_889919Z_build` PASSED the complete Quartus18.1 flow
in1267.797s, followed by27.453s explicit timing/CDC checks. Fitter finished
at17:47:18 Sydney time:29133 adjusted ALMs,40579 registers,356/397 M10Ks,
57/87 DSPs and2806736 block-memory bits. The placement column is32069.1
ALMs: the adjusted91% figure is not spare placement capacity promised to C.
The integrated core hierarchy uses20009.5 adjusted ALMs,49 M10Ks and33 DSPs;
this is not a separately fitted C-integration budget. VGA diagnostics now
use3945.2 adjusted ALMs and two M10Ks. Geometry and display stores inferred
real synchronous RAM.

All72 timing checks across four corners passed; worst setup/hold/recovery/
removal slack is+2.139/+0.118/+27.361/+0.393ns. Illegal/unconstrained clocks
and input/output paths are zero. All63 expected synchroniser chains appear
at each corner; MTBF acceptance remains NOT_ASSESSED.100 compiler warnings
were retained and reviewed: after source-path/line normalisation, there are
no new warning descriptions relative to7408a02d. The unchanged bounded
index/truncation/shift and signed-minimum sentinel warnings are explained
in `reader9_closeout/warnings_review.json`; no warning suppression or new
false path was added.

Programme `20261103T065044_691029Z_program` successfully downloaded the new
SOF **once**, to the discovered `DE-SoC [USB-1]` FPGAindex2,
`5CSE(BA5|MA5)/5CSTFD5D5/..`, ID0x02D120DD. Exit0 and board readback both
confirmed buildc63c9edb/public3/schema8. No persistent flash or Git remote
write was performed.

Fresh capture `20261103T065056_662337Z_capture` PASSED new-transaction,
CRC/schema, same-frame and all nine candidate pixel/model agreement checks.
Frame251 uses reader9/colour3, SW8=0 and SW9=0. All eight formal digits
(red1/2, blue1–6) were accepted; the uniquely paired BJ strip is valid with
quality255. Eight raw-RGB sampling frames completed automatic calibration:
cfg1, red33/blue28,204 red samples and324 blue samples; the last sampling
frame20 passed sampler/frame/pairing/geometry/window checks. Success event1
was issued at785857us. The capture spans9942193→10001632us, giving59.439ms
on the same board timebase. The event time is not an arm-to-commit interval.
Interaction is idle/armed, busy0, audioReady0. Current frameGood1 and
candidateOverflow0 coexist with the retained transport fault bit and two
startup drops; no zero-drop continuous-run claim is made.

The genuine image and acquisition identity are preserved as
`tests/fixtures/camera/frame251/`, PNG SHA256
`1d92356cf81fe7ac2e166b03ccc4d10fd45761f28ab14f33735b25425d574089`.
The final pose differs from earlier reference frames; no historical truth
regions or multi-trial scores were reused. One successful frame does not
resolve blue6 instability. By explicit user direction, this is the last
programme and development stops here: no new SW0/SW1/SW8/SW9 physical
confirmation, final90-frame trials, current41-check C bench or microphone
test was claimed. Historical tests remain available with their real sources.

Close-out materials are `reader9_closeout/receipt.json`, the source-bound
one-page `member_b_datasheet.pdf` (three-trial measurements explicitly
PENDING), and `member_b_ai_statement_draft.pdf` (student review unsigned).
The visible-message AI transcript is a read-only export of the identified
session; it excludes private reasoning/system/tool content and does not
claim to cover every project conversation. These local files are not a
Canvas submission. The final source/SOF hand-off archive is
`build/member_b/member_b_c63c9edb_closeout.zip`; its generated manifest records
relative file hashes and the exact SOF/source binding. No compiler database
or personal toolchain is included.

最终中文交接：c63c9edb已通过完整构建与四角时序并最后下载一次，板上身份
已核对。新frame251识别红1/2、蓝1–6及BJ，自动八帧校色提交cfg1/R33/B28，
单帧处理延迟59.439毫秒。蓝6稳定性按用户要求暂缓；当前R6总限时失败、
完整43项仿真中止及最终物理开关/三轮验收未执行均已明确记录，不能称全部
课程验收完成。README、OWNERS和本版本记录为维护入口，麦克风继续暂缓。

Read another fresh image without rebuilding/downloading / 继续读新图、不再下载：

```powershell
& 'C:/Users/15402/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/echo7.py --quartus-bin 'C:/intelFPGA_lite/18.1/quartus/bin64' --timeout 120 capture --fresh
```

## 2026-11-04：ECHO-7 整机修复与现场迭代

本次从 `github_publish/MTRX3700_MajorProject` 的 `dc1db23` 继续开发；外层旧工程及其
未提交 QSF 修改未覆盖。用户要求“主要功能一定实现、需要实机纠正、可以保留部分缺陷、
不过度跑”。因此先恢复同一生产顶层的真实视觉—控制—UART 链，再用有限的定向仿真、
完整 R6、Quartus 构建和架空实机逐层核验。后续用户明确追加红2启动、R6 285秒目标、
详细中英 README 与推送仓库要求；这些追加要求覆盖此前对应的收口安排。

### 版本与证据总览

设计build ID与CCTL接口版本是两个不同标识：以下设计为`E7070002`至`E7070009`，
接口仍为`E7070001`，不能把固定接口版本当设计版本。005已完成本版构建、R6及实际下载/读回，运动与整圈覆盖按末节实际记录分别判断。

| 设计版本 | 本轮主要变化 | 对应该版的自动验证 | 对应该版的真实板卡结论 |
|---|---|---|---|
| E7070002 | 集成 B/C、三模式、CCTL、完整安全链、红2重新选择、分页候选诊断 | Full Compilation 1203.431秒 PASS；R6 245.451876秒、12 PASS + CAUGHT | 21:23 AEDT 下载/读回成功；合成左中右、租约失效、预算结束、真实 IR 和轮向通过；真实蓝1可锁定，但后续候选溢出暴露健康资格永久阻断 |
| E7070003 | 将历史候选溢出诊断与当前健康资格分离；坏帧后建立新边界并等待三相邻新好帧 | 控制236检查 PASS；R6 221.258456秒、12 PASS + CAUGHT；Full Compilation 1154.491秒 PASS | 22:02 AEDT 下载/读回成功；保留历史flags=3仍恢复健康和锁定，无需复位；23个真实不同帧、22次锁定；真实红2暴露“启动早于第三帧锁定”问题 |
| E7070004（此前实板版本） | 未标定 INTEGRATED 红2必须等新请求目标完成三帧锁定后才启动；健康无目标不能提前消耗授权 | 控制254检查 PASS；R6 219.556074秒、12 PASS + CAUGHT；Full Compilation1121.141秒及门检25.868秒PASS | 22:31:50 AEDT下载/读回成功；真实红2新选择→新锁定→ARM/ALIGN通过；用户确认实物启动及蓝1脱离后停车，末VISION_ONLY/未ARM/左右0；后续地面首轮约75°后无效测距HOLD，未完成一圈 |
| E7070005（历史实板版本） | 真实左右证据确定旧转向反向，生产TURN_SIGN=-1；用户新要求下正常完整长回波为FAR、异常仍保护；d页FAr及主机分类 | 方向两参数各269检查、12帧pixel-to-UART、完整sonar46检查PASS；首次R6超时FAIL303.500928秒保留，最终13 PASS + 1 CAUGHT/239.403059秒；Full Compilation1173.143秒及门检25.799秒PASS | 01:11:16 AEDT下载/读回E5；蓝1零速8/8锁定、FAR6/6有效无HOLD，d页用户确认；三次满圈13.561176/11.075500/11.436358秒实测，实际设置13.6秒；首轮逆时针，约超10°/5°/45°，前两次起步前冲保留 |
| E7070006（时序验收失败） | ALIGN误差分档3/4cm/s，方向/速度/20–100ms脉宽锁存，转中/跨侧先停车；zeroSent后1.5s及新fence三帧确认 | 正/负各338检查/53UART PASS，5.2128905秒；14帧pixel PASS78.99106秒；完整R6 PASS266.840318秒、13 PASS+CAUGHT；compile工具exit0/1183.703秒，但整体验收因setup −0.265/−0.203ns FAIL | 失败产物未下载；3cm/s起转及1.5s机械停稳未证，不借用E5实物结论 |
| E7070007（历史实板版本） | 只将默认脉宽32位乘法链改为8位误差、10..50截限及17位移位减法；实际速度误差和非默认公式保留 | 256种U输入0差异；正/负各338检查/53UART PASS，5.113292秒；首次词法COMPILE FAIL保留；R6 PASS265.276162秒、13 PASS+CAUGHT；编译1147.755秒/门检26.087秒PASS，setup/hold +0.864/+0.117ns | 下载/读回成功；01/03窗口未ARM、02缠线/HOLD、04/05微动/过冲均未DOCKED；连续合成居中直行基本走直，促成E8 |
| E7070008（历史已验证版本） | APPROACH内U75–165连续正向差速，远5/3、近4/3；范围外或350mm偏心先零速/驻留/三新帧，再原ALIGN | 正/负各433检查/88UART PASS；R6 13 PASS+CAUGHT、270.641086秒；编译1159.722秒/门检25.963秒PASS；setup/hold +1.021/+0.121ns | 03:28:58 AEDT下载/读回；已见蓝1/3/4实相机落地DOCKED有用户确认，蓝3实体POWER；蓝2红2板上链及日志后运动分段佐证；最后蓝4画外搜索NOT_FOUND，5/6单独地面按用户要求取消 |
| E7070009（历史已发布） | 正向SEARCH看到后确认失败才有限反向回扫，150ms/全任务最多3步，反向同预算、每步完整停车重确认，中断不退款/不绕过驻留 | 两sign各696检查/245UART PASS；正式R6独立PASS274.530007秒；Full Compilation1218.109秒＋post-fit26.779秒PASS，setup/hold +0.629/+0.117ns | 原始SOF6706161字节已实际下载并核对E9身份；蓝4零速预检4/4锁定，画外蓝4搜索曾发现/锁定，但60秒观察窗未DOCK，主机STOP后零速，结果INCOMPLETE；反向SEARCH未触发，回扫实物效果未验证 |
| E7070010（历史已发布） | 默认U90–150居中，>350 mm且新锁定U75–165可在START/完整ACQUIRE后直接APPROACH | 定向ModelSim默认两sign各804检查/275UART、旧严格参数817/278，29.1663517秒PASS；正式R6独立PASS271.31444秒、13 PASS＋CAUGHT；Full Compilation1260.493秒＋post-fit25.832秒PASS，setup/hold +0.909/+0.118ns | 实际下载读回E10，零速蓝4校色预检4/4锁定；实机短暂APPROACH后LOST/SEARCH，最终NOT_FOUND/SCAN_BUDGET，未DOCK；无反向SEARCH，失锁恢复问题保留 |
| E7070011（当前已下载） | 停车调参及LOST完整重确认，保留先HOLD后丢牌旧分支边界 | runtime两sign996/358、legacy847/289；首R6 FAIL302.015209，最终PASS219.199994/13 PASS＋CAUGHT；编译1375.853秒＋门检26.278秒PASS | 原SOF6706153字节实际下载；真实JTAG停车调参/标定失效/默认恢复PASS，蓝4零速4/4锁定，首轮/search3搜索NOT_FOUND、turn3/turn5均INCOMPLETE，最终3/5/4/3/40对照仍INCOMPLETE，降速未消除抽动/过冲；停止追加测试 |

### 第一阶段：补齐控制契约和实际接口

实体 SW0–SW5 改为六位独热选择，20 ms 整组稳定后才接受；无拨码为 NO_SELECTION，
多拨码为 CONFLICT。未 ARM 时仍可 SELECT 和真实追踪。请求通过 ready/valid 握手，
当前正在等待接收的请求不能被新拨码覆盖；选择、配置、源切换和重新锁定均建立 tag/时间边界。
健康新帧、看见目标与三帧锁定分别记录，健康 NOT_FOUND 不再等同于视觉源坏掉。

生产 SOF 内包含 INTEGRATED、VISION_ONLY、CHASSIS_INJECT 三模式。第三种模式只替换
感知报告，沿用真实实体拨码、IR、J3、控制状态机及 UART；主机不能直接写轮速或伪造距离。
CCTL 提供状态快照、模式、START/STOP、注入和扫描参数；注入/调试会话有500 ms租约，
失约取消任务并发零速，恢复心跳不自动恢复旧任务。

运动流程包含有界 SEARCH、停车等待、ACQUIRE 驻留、ALIGN、APPROACH 及终态。
首次发现目标须先确认完整零速 JSON 已发送，再驻留200 ms、建立新采集边界、积累三帧新观测。
APPROACH 远距5 cm/s，500 mm以内3 cm/s，350 mm停靠；250 mm及以下危险/无效测距
进入安全 HOLD，连续三个真实新样本达到300 mm才恢复安全资格。IR A立即锁存停止；
第一次新的 POWER 仅解除 IR，第二次独立新按压才可启动，NEC repeat/持续按住不能算第二次。
这些行为经控制 TB、真实管脚时序模型及后续部分实机验证，证据层级保持分开。

### 第二阶段：用户追加红2、资源超限与有限范围优化

原附件中的红2 NO_ACTION 被用户明确追加需求替换为“重新取当前拨码、重新锁定并开始”。
实现范围为未启动/终态接收红2，活动任务不因反复呈卡重置累计扫描预算。
VISION_ONLY 只重新选择不 ARM；INTEGRATED 在安全条件满足后等待新报告；
CHASSIS_INJECT 不接入真实红2。红2须先移开三健康帧，再呈现三帧，上电已有卡不触发。
STOP、模式、IR、实体选择或安全边界清除旧授权；重新选择不清除已完成的红1校色。

首次构建 `20261104T094653_234340Z_build` 在追加需求后停止，其子流程仍留下
**32238/32070 ALM，无法 fit** 的报告。这不是通过构建，也没有下载该产物。
VGA 候选诊断随后从18组同时存储改为10组：每页8个候选，加中心与参考，
两页覆盖全部16个候选（含拒绝候选），默认每120个 VGA SOP切页，60 Hz下约2秒。
这次只做必要的分页资源调整，保留显示内容、中心关联和单HSV转换器。

主机工具方面，持久 STP 的 stdout 缓冲导致交互响应不可靠，改为显式 flush 的文件响应通道；
同一会话 STATUS/BSTATUS/STATUS 实测43/262/38 ms。Windows Verilator 环境按实际
编译器/DLL路径修正，未以模型或假结果替代 RTL 仿真。

R6 的失败与提速顺序保留如下，输入、断言和故意坏模块检测未删减：

1. 首次串行套件到300秒总限时后清理，实耗303.055秒，9项已通过、其余未完成，结果 **FAIL**。
2. 连续帧与过载两个独立系统场景在同次新编译之后并行运行，290.761秒，完整12项 PASS 和 CAUGHT；
   满足课程300秒，尚未满足用户新增285秒目标。
3. 编译并发 jobs=4 后，E7070002完整干净副本套件245.451876秒 PASS。
4. 每次后续生产 RTL 修正均重新运行完整套件：E7070003为221.258456秒，E7070004为219.556074秒。

这里复用的是**同一次调用**中生成的公共仿真二进制，由独立进程运行不同场景；没有拿上次构建的
二进制冒充当前源码。故意将三帧锁定改成两帧的私有 mutant 被原断言捕获为 CAUGHT，生产源码不变。

### 第三阶段：E7070002 构建、实机与第一个现场缺陷

E7070002 Full Compilation PASS，ALM29417/32070、M10K357/397、DSP51/87，
最差 setup/hold 为 +1.164/+0.078 ns，未约束路径0。21:23 AEDT下载本次新 SOF并读回
E7070002。用户确认底盘架空、SW0单独上拨、红1/蓝1在镜头前。

合成 U=80/120/160 实测逻辑轮速分别为(-4,+4)、(+3,+3)、(+4,-4) cm/s；
真实 J3约365–370 mm。失约后撤销授权并零速，续租不重启；1秒累计搜索预算耗尽后
NOT_FOUND并零速。用户确认观察到转向、同向转动和最终停止，另确认(+3,+3)时两侧实物均向前。
真实 IR A、第一次POWER只释放、第二次POWER启动也通过，测试后 STOP/VISION_ONLY。

首次真实画面中 A4 标牌贴边裁切，红色活动标签18超过15容量。保留原始 GRAB及模型复现，
用户将同张纸移远，再复位后24个不同帧中23次锁定蓝1（q255，U178/V181），红1完成8帧校色。
此后约20秒又发生单帧候选溢出；B历史 fault sticky 位导致 C 永久失去健康资格，
INTEGRATED 安全拒绝 ARM。这是现场发现的功能阻断，不能把之前的短时锁定写成持续成功。

### 第四阶段：E7070003 坏帧恢复与第二个现场缺陷

最小修正在感知适配器完成：历史 FAULT_CANDIDATE_OVERFLOW 仍保留诊断，但不永久禁止健康。
第一次 sticky 上升和每个匹配当前tag/config、时间新鲜、序号新的坏报告/RESOURCE_DROP
立即撤销旧健康、观测和锁定，建立**接收时刻**的新边界；旧管线好帧、重复帧、旧tag不能充数。
只有边界后三个相邻新健康帧恢复健康（允许 NOT_FOUND），目标锁定仍另需三帧有效观测。
FIFO、fatal、双bank硬故障仍阻断，没有通过忽略所有故障实现“恢复”。

该版控制236检查、完整R6、Full Compilation均通过。ALM29373/32070，
最差setup/hold +0.967/+0.117 ns，未约束0；22:02 AEDT新SOF下载并读回E7070003。
真实运行中frame338保留faultFlags=3，但健康和锁定已恢复，无复位；随后23个不同帧、
22次蓝1锁定，q255，U115/V186，处理延迟59.478 ms。这是本次已完成的真实故障纠正。

随后用户呈现真实红2，tag5→6证明重新SELECT生效。但第一健康报告尚未完成目标三帧锁定，
旧pending逻辑即发START；未标定扫描条件因此进入 SCAN_UNCALIBRATED/NOT_FOUND。
后续目标锁定也不会自动重启，用户看到“识别后无动作”。这个取消语义本身正确，问题是启动过早。
完整失败序列另存 `hardware_red2_e7070003_early_start.jsonl`，没有覆盖为后续成功。

### 第五阶段：E7070004 红2时序修正、板上通过与保留项

最小修正仅改变红2pending的启动资格：INTEGRATED未标定时必须等**本次重新选择后的当前目标锁定**，
前两帧ACQUIRING只能等待；已标定仍可凭健康新帧启动有界搜索。1秒授权窗口、STOP/IR/选择/
模式/安全取消、旧tag和旧帧隔离全部保留；健康无目标不启动，超时后的晚锁也不复活旧授权。

ModelSim控制自检254检查 PASS，实际解码15条UART，1.968秒；新增断言直接覆盖
前两帧不启动、第三帧锁定后APPROACH、无目标不启动、授权过期后不复活。
最终完整R6 219.556074秒，12 PASS + CAUGHT，满足用户285秒目标。
构建目录为 `build/member_b/20261104T111202_124373Z_build/`。

004 Fitter于22:28:38 AEDT成功：ALM29576/32070（92%）、寄存器41000、M10K357/397、
DSP51/87、memory bits2802640、PLL2。随后Full Compilation1121.141秒PASS、post-fit门检
25.868秒PASS，0 error/92 warnings；最差setup/hold +1.633/+0.118 ns、未约束0，
88项时序检查及每角63条同步链覆盖PASS，MTBF数值NOT_ASSESSED，没有放宽约束。
新SOF6706154字节于22:31:50 AEDT实际下载成功，BCTL读回E7070004匹配；
记录`build/repair/program_e7070004_console.log`。

随后真实红2板上链路通过：REAL_CAMERA/INTEGRATED、实体SW0选蓝1，tag3→4；
frame2900新锁定后ARM/ALIGN，逻辑L+4/R-4 cm/s、真实J3=468 mm、failure=NONE。
颜色已校准cfg1，但scanCalibrated=false，历史flags3仍保留；无需临时伪造扫描标定。
触发后2秒不发心跳，13个采样均ARM且leaseValid=false；7次ALIGN、4次LOST、2次ACQUIRE，
短暂丢失时零速重新确认，不能写成连续稳定转动2秒。触发和观察合计8个运动样本。
finally STOP确认未ARM、L0/R0、zeroSent=true，仍为INTEGRATED。

最终BCTL frame2959确认E7070004、蓝1q255、U182/V130、101×117框、frameGood=true，
处理延迟47.652 ms；红2事件7/id2、issuedAtUs115678441。
证据为`build/repair/hardware_red2.jsonl`和`red2_console.log`，003失败另存未覆盖。
用户确认004红2后实物会启动，最初反馈“不会自动停车”；随即收口到VISION_ONLY、未ARM和逻辑零速。
随后用户先确认“现在已停止”，再明确澄清“事实上是蓝一脱离后就停车了”。最终结论是004实物启动及
蓝1脱离后的实际停车已确认，撤去泛化的停车故障待查结论；不能把实际停止归因于切换模式。
主机两秒观察后STOP/zeroSent只说明板上撤销授权和零速JSON发送完成，其独立机械停车时刻未测，
不能写成两秒实物定时停车。红2开始正常任务并非两秒动作，架空也不能完成真实车体对准/停靠。
002的轮子/IR历史实测保留独立版本边界；按用户要求不再扩展硬件测试，继续文档和仓库发布。

该次发布时保留的范围限制是：落地三次一圈标定、六车位闭环、350 mm停靠误差、SW8正常/旁路公平对照、
实物超声危险及无回波边界、不同光照/遮挡，以及历史frame30321蓝6碎裂拒识。
004观察窗口仍有短暂LOST/ACQUIRE，持续视觉稳定性也明确保留。
后续架空J3/HOLD/STOP和SW8静态三对补验另列于下文；此处保留当时范围，不重复当作当前全未测。
架空转轮不等于地面360°标定，发完零速JSON不等于测量到车体物理静止。
当前无标定正式模式禁止无目标扫描，默认10秒只用于明确启动的合成调试；已锁定真实目标可接近。

迭代所引用的完整日志索引、命令、设计身份和验收边界统一保存在
[docs/REPAIR_RESULT.md](docs/REPAIR_RESULT.md)。本段记录的是开发与实际验证，不是课程完整验收、
Canvas提交或所有历史缺陷修复声明。用户要求的仓库推送由本轮最终交接另行记录。

最终发布SOF的仓库位置为`firmware/E7070004/PartBDebug.sof`，PDF位置为
`docs/ECHO7_Integrated_Datasheet.pdf`。PDF通过`tools/render_integrated_datasheet.py`
读取`docs/integrated_datasheet_metrics.json`复现（依赖reportlab/pypdf），旧`build/repair/`
过程文件不冒充最新发布物。发布SOF副本使用Quartus Programmer加载；`echo7.py program`
仍只接受本机成功构建记录中的原始SOF，不因整理文档而放宽产物身份核对。

发布前结构与打包检查另行执行：README白名单明确为`README.md`、`VERSION_README.md`（E14已将中英合为单文件）三件；对应结构测试6项PASS（1.613秒），实际仓库检查48个bench、60个
工程依赖PASS。submission已有14项测试PASS（0.226秒），导出包含英文README和最终PDF指标JSON；
OWNERS覆盖277个源文件，新增工具/测试按B+C与未知SID如实归属。这些是主机/结构验证，
不增加RTL测试数量，也不替代硬件证据。

### 2026-11-04，继续原任务：实体拨码观测与交接工具修复

用户随后要求继续原prompt剩余验收，覆盖前一阶段暂停扩展硬件测试的范围决定。
此轮工具/文档修改没有改变生产RTL、板上版本或SOF：仍为E7070004；最终完整R6仍是
219.556074秒、12项PASS与CAUGHT。本轮没有为工具修改重复R6或Full Compilation。

只读审查发现旧`echo7.py test --hardware --trials`的trial-stream仍会自动发送BCTL
SELECT/CLEAR，而正式顶层已由C独占目标请求。旧命令不能代表当前六档实体开关验收。
现将`test --hardware`及`autodebug`明确返回BLOCKED/退出2，指向新观测入口；
`autodebug`在replay、构建、下载与板卡访问前就停止。历史评分和重复牌检查保留，
没有修改旧观测或用自动选牌绕开实体开关。

`tools/chassis_debug.py observe`在一个持久STP会话里依次冻结读取CCTL和BCTL，支持
`--samples N`或`--seconds S`、`--out`与`--label`，正常退出只QUIT，不发送MODE、
SELECT、CLEAR、ARM、心跳或STOP。每个端点的内容和主机读取区间独立保存；不把两次冻结
称为同帧。所有bad、unlocked和held轮询保留，另计不同帧数；Ctrl+C/传输失败也保存
已读部分。COMPLETE表示采集完成，不是功能PASS，输出文件不可覆盖已有记录。

`tools/compare_observations.py`离线比较正常/旁路各三次观测，要求同一构建、配置值、
实体目标、运行模式和poll数，单次内部请求/config稳定，SW8分别0/1且SW9关闭。
它拒绝重复使用一次run和错误时间顺序，分别统计全部轮询与不同帧；坏帧、丢锁、陈旧和
延迟值不会被删掉。没有操作者真实条件确认则UNCONFIRMED_CONDITIONS/退出2。
COMPARISON_VALID仅表明可比较，不能升级为六车位落地闭环、停靠或图像到UART延迟验收。
当前摘要中的延迟只来自FPGA capture/completion时间戳。

合成`scenario no-target-search --arm`改为读取当前scanBudgetUs，保持模板“预算＋3秒”，
覆盖最终零速、200ms停稳、900ms确认及轮询余量。同一会话持续记录状态并分页续租，
不再到默认10秒就抢先STOP；退出仍尝试STOP。HOLD期间不累计搜索转动时间，因此不能
仅根据会话时长宣布预算耗尽，也没有设置或伪造地面扫描标定。

导出器此前只把SOF放在`verified/PartBDebug.sof`，导致包内README的`firmware/E7070004/`
链接断开。现在只归档一份已核对当前构建的SOF，路径按构建ID生成
`firmware/<BUILD_ID>/PartBDebug.sof`；简短build_record记录包内路径和原始本机产物位置。
实际smoke ZIP验证了唯一SOF、当前README固件路径、PDF、CRC及与本次构建SOF字节相同。
这次smoke不代表随后所有新增实机记录与文档都已打入最终交接包。

针对检查实际完成：chassis/旧入口保护/submission共27项PASS（0.408秒），
新观测比较器及保留的历史评分/重复牌回归共32项PASS（0.505秒）。这些共59项均为
主机测试，部分使用明确的合成fixture，不增加任何实机或RTL通过数量。
OWNERS新增观测比较工具及其测试，当前279个文件；自动生成器同步保留B+C归属与
A/C SID pending，未杜撰成员身份或人工签核。中英文README补齐对应命令和边界。
后续六牌、六档实体选择及SW8实测结论以根代理核对后的独立原始记录为准，未在此预填成功。

### E7070004续测：完整六牌、六档实体选择和非法组合

根代理随后完成真实相机只读采集，vision根据全量记录生成
`build/continuation_20261104/vision_findings.json`与`six_switches_analysis.json`；
完整表见`docs/REPAIR_RESULT.md`末尾。本段只追加已核对的零运动视觉证据，不改变004源码、
219.556074秒R6或已发布SOF的身份。

用户将六张蓝牌完整置于画面，并用绿色胶带遮住红2。GRAB frame26844像素/结果同帧，
CRC0x80b8核对通过，E7070004、cfg1、红57/蓝37、正常透视、非raw；六张蓝牌均接受且q255，
处理52.889ms，无候选溢出。另12个不同B帧中六张蓝牌分别12/12接受，所选蓝1为
C健康/锁定12/12；全程VISION_ONLY、未ARM、零速。遮住的红2残余和参考条没有被伪造为数字。

实体SW0–SW5及非法选择续测运行150.054秒，保留441对完整只读采样，B为441个不同帧、
C为405个不同缓存帧。六个one-hot都实际锁定对应蓝牌；主要区间的N/C健康/C锁定/B锁定为：
蓝1=200/200/197/197，蓝2=23/23/22/22，蓝3=28/27/24/24，蓝4=22/19/16/15，
蓝5=29/28/23/23，蓝6=30/30/26/26。另有蓝2短过渡1次未锁，冲突后返回蓝1为
64/63/62/62，首对仍保留旧tag25 CLEAR而C已请求tag26；C没有接受旧报告为新锁。

全零NO_SELECTION共17次，CONFLICT共27次，其中稳定mask3为26次，另一次是mask6过渡。
这些非法选择均无C健康/锁定且B未选择目标；全441对均VISION_ONLY、未ARM、无运动许可、
逻辑L/R=0。C总健康390/441、锁定370/441，B好帧434/441。7个坏B帧全部是candidateOverflow，
没有candidateError/overrun，每次坏样本后均观察到好B帧；仅部分在同一选择结束前观察到双锁恢复。
完整坏帧/过渡记录保留，不能写成441次无丢锁或无坏帧。

CCTL先读、BCTL后读，两端分别冻结，因此一对中C尚锁定而稍后B出现新坏帧，不证明C接受了
该坏帧继续运动。读数间0.306–0.699秒见到好B、部分读数间恢复双锁，都不是精确原生帧恢复
或物理拨动到锁定延迟。本轮建立六档真实视觉选择覆盖，仍未替代六车位落地闭环。
该阶段结束时SW6/7显示、SW8三对公平试验、J3危险/无回波/距离边界与地面扫描标定待验；
后续新增的显示、J3及STOP证据见下方续测记录，不追溯改写当时的验收范围。

### 数码管使用说明澄清（生产RTL不变）

核对`memberCBoard.sv`后明确：d页HEX3–HEX0为十进制毫米，左侧HEX5页标识及HEX4模式
不属于距离；例如`d2 0520`是CHASSIS_INJECT模式下520mm。KEY1循环d/H/L，H/L显示NEC
遥控码；距离无效时右四位全熄灭。显示、控制及JTAG取自同一distance_mm，测量约100ms更新，
JTAG快照和现场观看不是同一时刻采样。中英文README已同步。

现场反射板摆位调整前后曾读到379mm与520/521mm；尚未核定真实反射面、尺子起点和绝对误差。
没有根据这次摆位差异修改换算系数，也未据此宣称距离标定或所有物理边界验收通过。

### E7070004续测：J3停靠、HOLD复核及独立STOP

生产RTL、板上版本及发布SOF仍为E7070004，最终完整R6仍为219.556074秒；此次只修正
一次性主机验收脚本和记录，没有重新编译RTL或重复R6。以下运动试验全部为合成视觉、
真实IR/J3/UART、架空底盘；原始记录及分析位于`build/continuation_20261104/`，
可移植说明见`docs/REPAIR_RESULT.md`。所有失败、未确认项及清理记录保留。

| 试验 | 记录与结果 | 实物确认及限制 |
|---|---|---|
| SW6/7显示 | SW6颜色信息可见；SW7中心在白色空隙显示局部颜色和“无标牌” | 用户确认；SW6两页/16槽/UNKNOWN/拒识原因及SW7中心覆盖牌/歧义仍未确认 |
| 停靠01 | `dock_hardware_01.jsonl`、`dock_analysis.json`；434快照/78.931565秒；首次变化为517mm、逻辑+5/+5→446mm、+3/+3→347mm、DOCKED/撤权/零速 | 用户确认运动、减速、停车、退远不重启；534–615mm退远窗口12快照/2.194秒仍DOCKED/零速；不是落地停靠误差 |
| HOLD01 | `hold_hardware_01.jsonl`、`hold_analysis_01.json`；362快照/66.181秒，板上条件PASS | 用户未确认实物全过程并要求重做，不算物理恢复验收 |
| HOLD02 | `hold_hardware_02.jsonl`、`hold_analysis_02.json`；434快照/79.899秒，原FAIL保留 | 用户未见恢复；主机在滞回观察未满1秒时抢先STOP，截断已开始的ACQUIRE，不证明生产RTL恢复失败 |
| HOLD03 | `hold_hardware_03.jsonl`、`hold_analysis_03.json`；469快照/86.677721秒，6项条件PASS、notVerified为空、清理无错误 | 用户确认近停、滞回仍停、退远恢复、随后自动停；本轮未观察轮向，未测机械停车延迟 |

停靠01首次DOCKED后83快照/14.853秒保持撤权/零速，包含退远窗口；条件确认点
521/454/321mm来自随后不同快照，不与首次变化517/446/347mm混为精确距离边界。
全部数值为真实J3报告读数，未校准尺子起点、反射面或绝对距离误差。

HOLD02尾部为237mm HOLD→251/254/266/292/297mm（滞回区间记录跨度仅0.652370秒）
→305mm HOLD→313mm ACQUIRE。79.860570秒末样本仍ARM、sonarHold已解除、逻辑零速，
租约/来源/目标锁定有效；79.860697秒主机即请求STOP并随后切mode1，阻止恢复转动被观察。
脚本现将提前安全恢复且尚未满1秒的阶段记为NOT_VERIFIED并继续、总结果为PARTIAL，
避免把不完整试验误写成生产缺陷或PASS。硬件恢复规则仍为三个新的有效样本≥300mm，
并非固定等待1秒；HOLD03完整满足主机要求，无跳过或PARTIAL。

HOLD03危险确认窗口231–242mm：5快照/0.647892秒HOLD/零速；滞回254–292mm：
7快照/1.163541秒仍HOLD/零速；退远367–407mm：19快照/3.119478秒恢复ALIGN，
逻辑−4/+4。恢复观察满3秒后，80.491761秒显式TX4 STOP，继续原模板及心跳。
STOP ACK至末快照6.093588秒，34个不同帧的状态快照均未ARM、零速且zeroSent=true；
首末快照跨度5.919557秒，原生frameId推进147。J3始终有效且为367–376mm，租约、来源、
锁定持续有效，sonarHold/IR/fatal均否，模式、选择、tag及配置不变，之后才切mode1清理。
因此本次停止和不自启有独立于失约、目标丢失、危险距离及切模式的记录；用户也确认停车。
34次为状态轮询，不是独立测距次数；持续描述指全部已记录样本，不能排除采样间变化。
本次结果不补证早先真实红2试验中未隔离的主机2秒STOP物理时刻，也不测机械停车延迟。

本轮结束于VISION_ONLY、IDLE、未ARM、逻辑零速、zeroSent=true，用户确认已停。
该阶段结束时尚待：无回波实物测试、SW8正常/旁路三对公平试验、SW6翻页及拒识/UNKNOWN全槽确认、
SW7中心覆盖牌/歧义、地面扫描标定与六车位闭环、精确距离/停车误差，以及A/C成员SID。
后续静态SW8三对、自动翻页、中心蓝1和首次地面中断记录已追加于下文，不把此历史清单当最新状态。
HOLD03本轮轮向未观察，未因此再扩展硬件运行；早期其他版本的轮向证据仍按版本单独保留。

### 2026-11-05：断电恢复、SW8三对静态对照和VGA补验（E7070004不变）

用户改为底盘供电后FPGA曾断电，JTAG也一度不可见；恢复电源和编程连接后，重新下载
本次已完成Full Compilation的E7070004实际SOF，程序下载及板上build ID核验成功。
日志在`build/remaining_20261104/reprogram_e7070004.log`。此前未完成的GRAB和连接失败
记录保留，没有将旧图像当成重新上电后的当前图像。生产RTL、发布SOF、219.556074秒
的R6和原fit/timing结果均未改变，未为纯硬件观察重复编译。

重新上电后的首张同帧GRAB显示标牌过小、偏画面边缘，未形成有效候选；用户调整纸张
完整入镜并确认镜头到纸张约42厘米（纠正先前口述42毫米）后，默认红48/蓝20、未校色
配置下六张蓝牌各连续6/6接受，蓝1健康锁定，VISION_ONLY全程未ARM和零速。
这次记录与断电前的红57/蓝37校色结果分别保留，不假设校色参数跨断电保存。

实体SW8依次采normal1/bypass1、normal2/bypass2、normal3/bypass3，各12个C/B配对。
第一次会话在等待normal2拨码时达到180秒阶段期限，退出PARTIAL，总229.014756秒；
已完成的第一对及等待日志未覆盖。新会话只续采其余四段，用时80.414576秒，并保存
原始超时来源及各段实际路径；不是六段全部来自同一个会话。用户对保持相机、纸张位置、
光照不变的确认题回复“done”，比较工具输出COMPARISON_VALID。两次会话均只读STATUS/
BSTATUS，没有选择覆盖、START、注入、心跳或STOP命令。C/B分别冻结，不宣称同帧。

| 静态对照 | 正常透视，3轮合计 | 实体SW8旁路，3轮合计 |
|---|---|---|
| 配对数及不同C/B帧 | 36，各端均36个不同帧 | 36，各端均36个不同帧 |
| 六蓝牌各自接受次数 | 蓝1–6各36/36 | 蓝2为35/36，其余各36/36 |
| 选定蓝1的C/B健康锁定 | 36/36 | 36/36 |
| 当前坏帧、候选溢出/错误、重复帧 | 均0 | 均0；但有一次有效候选拒识 |
| FPGA采集至处理完成平均时间 | 53.240667毫秒 | 42.578861毫秒 |
| 未ARM、无许可、L/R零速、zeroSent | 36/36 | 36/36 |

旁路第二轮样本0/frame20748，蓝2位置的candidate#5被reader uncertain拒识，quality0，
reason3；下一采样frame20763同位置恢复蓝2/q255。该帧仍为好帧，不能把“无坏帧”写成
“所有候选全部识别成功”，也不能由一个抽样失败推断持续缺陷或透视算法的普遍优越性。
各段采样数和配置匹配，实际采集用时不完全相等；数据只覆盖这些静态轮询，不代表所有
相机原生帧、地面六车位任务、正常/旁路地面各三次闭环，或图像变化到实际UART响应延迟。
详细表和原始文件索引见`docs/REPAIR_RESULT.md`；本次未新增逐文件哈希报告。

完成对照后，用户明确目视确认SW6的PAGE:1/PAGE:2自动交替；当前六候选时第二页为空
符合预期。随后移动纸张使蓝1覆盖中心小框，用户确认SW7显示ID:B1，之后恢复仅SW0上拨。
这两项补齐翻页和中心有效标牌身份的实物观察；UNKNOWN/拒识原因、16个满槽及中心歧义
并未随之全部验收。显示补验后的只读预检为配置7、colourCalibrated=true、蓝1健康锁定、
J3为386毫米且有效、IR未锁存、VISION_ONLY/零速；不将对照期间的默认未校色配置延续到
纸张移动之后，也没有读取或猜测这次新校色的具体阈值。

用户已确认底盘落地、周围可容纳一整圈、编程线缆可安全安排；地面标定和真实视觉停靠
在下一阶段单独记录。本节没有落地运动通过结论。断电/重新配置后扫描仍默认10秒且
未标定，不能将这个缺省值写成实测360度或已保存的一圈标定。

### 2026-11-05：E4地面首轮失败、左右实图核对与E5候选修正

本轮先执行E4真实落地试验，再定位问题、接受用户新规则并修改候选源码。没有先假设
硬件转向符合RTL中的left/right命名，也没有把原先的直行/架空动作通过当作真实视觉
闭环已通过。下述原始记录在`build/remaining_20261104/`，旧E4日志及已发布SOF均保留。

**地面与首轮失败。** `ground_scan_01.jsonl`为78个CCTL快照、21.518290秒，
结果TRIAL_INVALID，cleanupErrors为空。用户最初口述环氧树脂，后明确纠正当前测试
地面是**塑胶地板**，实验室才是环氧树脂；原日志首行不改，`ground_operator_notes.json`
补记更正。输入为健康合成NOT_FOUND、真实J3/IR/UART、实际落地底盘，临时预算60秒，
scanCalibrated=false，不是相机找牌或停靠任务。

一次START后12个SEARCH快照均逻辑L/R=−4/+4，实际有效J3为434–1702mm；相邻移动
快照的FPGA timeUs与scanElapsedUs增量差全部为0。21.457927秒的记录已进入HOLD：
raw4000、distanceValid=false、sonarHold=true，ARM保留但permit=false、左右0、zeroSent=true；
source/lease仍健康，IR没有触发，累计SEARCH命令时间2,899,142us。主机随后才请求
STOP并切VISION_ONLY，因此无效测距保护先于主机清理。最终仍未ARM/零速，清理无错。

用户确认约转75°后停下；首次方向口述有自我更正，后按**俯视**再次询问，明确回答
**顺时针**。用户另说明停下朝向前方空旷、未放恢复回波的纸板。该场景说明、近似角度
及电气状态各自记录：没有测原始ECHO波形，不能只凭4000判定电气唯一原因。首轮
没有完整360°、没有IR终点，三次整圈接受数仍0/3；不把75°或2.899142秒比例外推成标定。

**左右静态证据。** 车体固定后，同一蓝1从前左移到前右。`body_left_01.json`有
6/6完整C/B配对，U80、V158–159、J3 442–450mm，耗时3.426745秒；
`body_right_01.json`有6/6配对，U174、V157、J3 436–440mm，耗时2.810337秒。
两次C/B各6个不同帧，目标健康锁定，无坏帧，E4/cfg7、正常透视、红24/蓝20，
全程VISION_ONLY/未ARM/零速。用户明确VGA左半蓝1就是车体实际前左，U向右增加而V
基本不变，排除把低U当右侧或错用垂直轴的解释；C原样使用centreU，不做隐藏镜像。

结合ground01逻辑−4/+4实际顺时针，旧低U ALIGN确实背离车体左目标。此次定位为
**有效视觉转向反向**；双轮同号直行不能排除真实左右通道互换，本轮不再扩大单轮追线，
不声称已经证明某条接线错误。候选E5只将生产顶层TURN_SIGN默认+1改为−1，经已有
参数链影响SEARCH及两侧ALIGN，原左右极性−1/−1、居中+5/+5与+3/+3保持。
低U/SEARCH新逻辑(+4,−4)，按既有UART编码输出L−0.04/R+0.04；高U相反。
没有交换U/V、改变像素样本、翻转合成坐标或更改前进符号。没有运行时方向CLI；
需要新构建/下载后验证实际朝向目标，新一圈标定必须用最终方向及当前地面。

**随后用户改变正常无回波规则。** 用户明确指示“超声波读不出数据时可认为前方障碍
无限远，此时不应该应急停机”，覆盖附件原先所有无回波均禁止运动的规则。E5候选
在range驱动约23.3ms到上限后等待该次真实ECHO回低；本次有实际TRIG/有效回波过程、
长脉冲完整结束且未到80ms事务期限，才发布4000/valid=true的FAR哨兵。没有触发/
上升、恒高不落、期限到达或过短异常仍invalid；近≤250mm和IR保护不变，恢复仍需
连续三个新的安全样本≥300mm。每100ms事务和陈旧检查保留。FAR不是实测4米，也不
证明车体四周空旷；旧E4的4000/valid=false记录不回改成FAR。

板上d页仅在valid+4000显示FAr，H/L遥控页不变，invalid仍空白；主机decode新增
distanceFar和distanceKind（FAR/MEASURED/INVALID）。正常量程外与异常信号的实物
分界、新方向接近停靠在本段修改时仍待E5下载后验证；后续本版下载及静止FAR实测
已完成，见末尾新记录。正常空旷FAR不等于异常信号边界或运动闭环全部验证。

**新增聚焦回归。** 当前`tb_control_repair`使用显式负生产参数，269项/20条完整UART
PASS；同bench正参数泛型对照也269项PASS，不累加成538项独立需求。覆盖SEARCH、
低/高U完整JSON左右字段、U109/110/130/131边界、两段直行与STOP完整零。编译及
两次ModelSim总3.367385秒，日志为`turn_e5/control_negative.log`、`control_positive.log`。
`tb_pixel_uart_repair`固定25fps、原12帧真实RGB565管线输入不改，显式TURN_SIGN=-1，
12帧/12报告PASS；SEARCH41、低U18、前进39、高U34、zero118条完整UART。
Verilator5.050编译12.529247秒、运行71.835396秒、总84.364643秒，日志`turn_e5/pixel/`。
这些是RTL_SIM和编码验证，不是新版本实物方向测量或完整R6。

独立`tb_sonar_guard`在完整生产时钟尺度的模拟引脚回波下46检查PASS，12输出样本、
11次TRIG，覆盖24/39/75ms完整长脉冲、80ms恒高/晚落沿、无上升/无触发异常、近距及
新事务恢复。新副本Verilator编译5.821181秒、运行83.748601秒、总89.572575秒；
结果为`sonar_guard_verilator_20261104T133057_380747Z/result.json`。前一次
`...T133013_823304Z`编译exit255/MSYS权限异常记录保留（0.233933秒，未进入RTL仿真），
没有被成功重试覆盖。这里是模拟ECHO波形的RTL_SIM，不是传感器实物或完整R6。

同一sonar bench另有显式`+R6_REPRESENTATIVE`六事务路径，独立新副本运行25检查/
6样本/6次TRIG PASS，编译5.834637秒、仿真38.076932秒、总43.912875秒。
`sonar_guard_representative_20261104T133440_446720Z/validated_result.json`核对实际
退出0及PASS行；原包装器因PASS行新增scope字段而误报的`result.json` FAIL保留，
没有重跑或改RTL。完整46项边界路径仍在，代表路径不替代完整边界覆盖或完整R6。

**E5首次正式完整R6失败。** `build/member_b/20261104T133634_057221Z_verilator_course/result.json`
记录FAIL、退出1、303.500928秒、targetMet=false。新源码副本、Verilator5.050、jobs4，
目标285秒、总期限300秒不变；新增sonar后共有13个正式bench及mutant检测。前12项
pixel、control、CCTL、red2Start、sonar代表、continuous、overload、HSV、tracker、
fixedSheet、colourSampler、markerQueryStore均PASS；`mainColourSupportReader_tb`
编译达到整套截止时间，故意坏模块尚未执行。清理耗时计入实际303.500928秒；不写
CAUGHT、不写全部功能断言通过，也不借用E4的R6通过结论。

随后仅优化独立pixel/sonar仿真的并行调度，保留原continuous/overload并行、全部13项、
输入、断言及285/300秒标准，不复用前一次调用的二进制。为避免资源竞争，等E5完整
编译结束后才启动优化R6；最终实际13 PASS + 1 CAUGHT、239.403059秒、targetMet=true，
61个新复制源文件、cleanBuild=true、jobs4，结果在
`build/member_b/20261104T140614_115616Z_verilator_course/result.json`；日志为
`build/remaining_20261104/r6_e5_parallel_console.log`。生产RTL、TB、runner、输入均冻结。

**E5 Full Compilation实际完成。** `build/member_b/20261104T134331_185490Z_build/result.json`
记录PASS、退出0，Quartus Prime Lite18.1.0 Build625，compile1173.143秒、post-fit门检
25.799秒、0 errors/92 warnings，结果完成2026-11-05 01:03:31 AEDT。ALM29507/32070
（92%）、regs40957、M10K357/397、DSP51/87、memory bits2802640、PLL2；新SOF
6706157bytes，位于该build的`source/quartus/output_files/PartBDebug.sof`；后续已使用
此原始产物实际下载并读回E5，不把文件复制当作下载证据。

已读取本版`timing.json`、报告门与同步链覆盖数据：四角setup/hold/recovery/removal
均非负，最差setup+2.089ns、hold+0.116ns；88项报告检查，Illegal Clocks及所有列出的
未约束clock/input/output port/path为0。每角Gray9/9/32位timed path和同步级setup/hold
完整；resultToCamera1589位/requestCdc22位setup覆盖，resultToDisplay979物理端点
覆盖完整；max-skew与net-delay最差裕量18.013ns/13.647ns。每角63条预期/实际同步链
coverage PASS，MTBF验收NOT_ASSESSED。这些是本次真实结果，不沿用E4数值。

**当前发布门状态。** E5首次R6超时FAIL保留，最终优化R6 PASS239.403059秒；完整构建、
post-fit、原始SOF下载和E5读回均PASS，零速蓝1/FAR实测通过；实际有效转向、
真实视觉闭环及固定预算自动停车角误差仍未完成；FAR期间SEARCH和三次满圈已有记录，13.6秒近似上限已实际设置。004的219.556074秒、1121.141秒、
ALM29576和时序成绩继续只归004。E5单圈脚本独立保留，先读回E5再准备新SEARCH，
允许valid FAR、每次新ARM一次、真实IR A终止；真实INTEGRATED观察脚本不发START/
注入/心跳，等实体POWER，DOCKED保持3秒与NOT_FOUND分开。脚本就绪不算已经运行。
实际结束状态为E5 VISION_ONLY/未ARM/零速；三次一圈、六车位落地闭环、SW8地面对照、
实际停止误差与端到端延迟继续保留待项。详细证据及后续真实结果在
[REPAIR_RESULT.md](docs/REPAIR_RESULT.md)追加，旧失败不被候选修正覆盖。

本轮生产变更集中于`echo7IntegratedTop.sv`默认方向、`memberBBuildId.svh`身份、
`sonar_guard.sv`有界FAR分类及`memberCBoard.sv`距离页；主机解码在`chassis_debug.py`。
控制、像素和超声专项bench分别保留对应边界，manifest/suite纳入sonar代表项。
完整文件索引及测试层级见验收报告末节；源码冻结不表示新SOF已构建或板卡已下载。

**E5实际下载与静止实测。** 在完整R6及构建通过后，使用本次成功build的原始SOF下载，
`build/remaining_20261104/program_e5_console.log`记录PASS、programmerSucceeded=true、
buildIdVerified=true，实际读回E7070005；UTC2026-11-04T14:11:16.707754完成，换算
AEDT为2026-11-05 01:11:16.707754。构建完成时间与下载时间分别保留。

随后`e5_zero_scene_01.json`在3.045175秒取得8/8完整C/B配对，各8个不同帧；蓝1
healthy/observed/locked全部通过，U170/V159–160，J3真实432mm有效，VISION_ONLY/IDLE、
未ARM、左右0、zeroSent=true，无HOLD。实际校色配置1、红24/蓝16，colourCalibrated=true，
scanCalibrated=false，历史faultFlags3保留。C/B分别冻结，配对不冒充同一时刻快照。

用户移开挡板后，`e5_far_01.json`在2.270134秒取得6/6完整配对，均valid4000、
distanceFar=true、distanceKind=FAR、无HOLD、zeroSent=true；用户确认实际d页显示far。
此时健康但无目标，observed/locked=false，全程VISION_ONLY未ARM/左右0。4000是FAR
哨兵，既不代表测得4米，也不记录原始ECHO波形；静止读回不能证明运动期间的FAR行为。
这两项是E5真实硬件观察，不沿用E4结果；本版有效转向、连续整圈及地面停靠尚未验证。
截至这两组静止观察时，新版圈数为0/3、首圈尚在准备，没有写入标定；随后首轮执行结果单列如下。

**E5第一轮地面IR计时。** `ground_e5_01.jsonl`记录总34.960365秒、197个C快照，
IR_TERMINATED_TIMING_CAPTURED，failure/cleanupErrors均空。塑胶地板、当前整车及
底盘供电，健康无目标合成视觉、真实J3/IR/UART，临时60秒未标定预算；不是实际视觉
搜牌/停靠任务。80个运动快照全部SEARCH、逻辑(+4,−4)、source/lease健康、ARM/permit，
无HOLD/invalid/fatal/身份变化。70次MEASURED快照377–3120mm，10次FAR4000，分为
2/1/7次三个窗口，最长采样首末1.072009秒；快照次数不当作独立超声采样次数。
相邻79对真正运动快照timeUs与scanElapsedUs增量差−1..+1μs，未观察到计时中断。

实际IR快照先读到锁存、未ARM、IDLE、左右0、zeroSent=true，累计SEARCH **13.561176秒**，
随后主机才STOP及切VISION_ONLY。最终V1/未ARM/左右0、IR仍锁、J3379mm有效。
用户确认“转满一圈多一点点，同时转完后相较于起始是往前了一些”，原话保存在
`ground_e5_operator_notes.json`。这是1次满圈且轻微超转/前移的观察；最初旋向及误差待补，后续补充见下段，
不把IR终点累计时间冒充精确360°时间，不据此永久标定。
随后用户补充“逆时针，多了大概10°，前移约3.5cm。第二圈就绪”，原话已保存：
首轮可计物理满圈**1/3**，旋向为俯视逆时针；约10°和3.5cm是用户估计，漂移误差保留。
首轮阶段尚未写入参数，未将13.561176秒按估计角度缩放成精确360°；后续三圈汇总与实际写入另列。

当前E5固件发布副本为`firmware/E7070005/PartBDebug.sof`，6706157bytes。使用原始成功
build实际下载及读回的记录独立保留；历史E4发布路径继续只描述当时归档。

**E5第二轮满圈及启动不对称。** `ground_e5_02.jsonl`记录27.025306秒、146个C快照，
IR_TERMINATED_TIMING_CAPTURED，无failure/cleanupErrors。66个不同帧运动快照全为
SEARCH逻辑(+4,−4)，source/lease/ARM/permit和J3有效，tag6/配置1/蓝1保持，无HOLD/
fatal/提前IR。53个MEASURED快照395–1686mm，13个FAR快照分2/5/6次三段，最长采样
首末0.751414秒；65对相邻运动计时增量差−1..+1μs。IR先读到未ARM/零速发送完成，
累计SEARCH **11.075500秒**，随后主机STOP/mode1；末VISION_ONLY零速、IR锁、404mm有效。
随后用户确认“满一圈，多5°，前移大概2cm。然后我发现主要是启动的时候左右轮动力
输出不均匀，都出现了单边前冲的情况”。第二圈实际满圈成立，累计物理确认**2/3**；
约5°及2cm是用户估计，不当作精确传感器测量。两轮启动单边前冲/动力不对称作为实际
缺陷现象保留，尚不能归咎UART、接线、电机、摩擦或电源中的具体根因。当前只读核对
命令链，第二轮结束时尚未写scanCalibrated；后续第三圈与参数写入另列，仍保留两次
实际时间与漂移，不用期望值替换日志。

**E5第三轮满圈及实际13.6秒设置。** `ground_e5_03.jsonl`为151快照/27.078186秒，
IR_TERMINATED_TIMING_CAPTURED、无failure/cleanupErrors、累计SEARCH **11.436358秒**。
70个不同帧SEARCH快照全(+4,−4)、ARM/permit/source/lease/J3valid，tag8/配置1/蓝1不变，
无HOLD/fatal/提前IR；55个MEASURED402–1689mm，15个FAR快照分2/5/8次三段，最长采样
首末1.175691秒。69对相邻运动计时增量差−1..+1μs。实际IR撤ARM/零速发送完成先于
主机清理；末VISION_ONLY零速、IR锁、432mm有效。随后用户确认“满圈，我按晚了，
多转45°，没有单侧前冲”：三次满圈确认**3/3**，第三轮超转约45°含明确按晚误差，
没有观察到单侧前冲，位移未提供不补猜。后两次旋向没有另行口述，命令与首轮相同。

三次板上时间13.561176/11.075500/11.436358秒，最大最小差2.485676秒，均值12.024345、
中值11.436358；二者分别比最大少1.536831/2.124818秒，可能不能覆盖最慢实测轮次。
三圈物理确认后，已将最大值向上取**13.6秒**作为覆盖本次记录的有界SEARCH上限，
比最大多38.824ms，不保证未来条件下精确360°，快轮可能多转。
不按用户约5°/10°反馈缩放原始时间，保留起步前冲、超转、前移和人为终点判断边界。

实际CLI输出`e5_scan_calibrated_13600ms.json`读回scanBudgetUs=13600000、
scanBasis=CALIBRATED_TIME、scanCalibrated=true；VISION_ONLY/IDLE未ARM、左右0、
zeroSent=true、IR仍锁，J3421mm有效，没有START。旧scanElapsed11436358是前一轮的
保留计数。该运行时参数跨普通模式切换保留，reset/重新下载会清回10秒未标定默认，
没有烧成永久参数。只适用于已记录的当前塑胶地板、整车及底盘供电；实验室环氧地面
未测。尚未验收固定13.6秒预算自动停止时的转角误差，随后真实蓝1任务已执行但NOT_FOUND，不能记停靠
通过；起步前冲前两次出现、第三未出现，根因仍未证明。

只读UART源码审查确认，生产启用独立左右请求，IDLE同一时钟沿生成并冻结含L/R的完整
JSON，SEND逐字节发送，不逐侧拼旧值。此结论不证明底盘对端解析、电机施力或机械起步
同步，不能消除用户看到的单边前冲；没有据此归咎或修改单一硬件部件。

### 2026-11-05：E5真实蓝1失败、短转过冲诊断与E6候选

**先记录真实失败，再修改控制。** `integrated_blue1_01.jsonl`原label为visible_left，
但用户在独立preflight后已把蓝1移出视野，实际POWER前是健康NOT_FOUND；原日志不改，
场景更正在`integrated_e5_operator_notes.json`保存。实体POWER启动，主机START/合成写入/
heartbeat均0。任务结果**NOT_FOUND / SCAN_BUDGET**，不是DOCKED：656快照、全程观察
73.006122秒，首次ARM至终态36.330141秒，搜索累计达到13.600000秒后零速且未ARM。
主机随后STOP/mode1，cleanupErrors为空。任务段335不同C帧、蓝1/tag10/配置1保持，
真实J3valid、无HOLD/IR/fatal、lease=false；状态SEARCH128/ACQUIRE49/ALIGN129/LOST23/
APPROACH5/NOT_FOUND1，未完成真实停靠。

首次ACQUIRE实际是观察ARM后约**1.200秒**，第一次确认失败后约+2.320秒回SEARCH；
约+12.637秒是后一次ACQUIRE，+12.970秒才首次ALIGN，不能写11秒后才首次发现。
之后8个LOST窗口、9个ALIGN窗口反复，APPROACH仅5个+5/+5快照、613–663mm；
SEARCH累计在纠偏期间保持11.205106秒，后继续搜索到13.6秒并最终确认失败。CCTL没有
逐帧U/B拒识原因，不能唯一断言丢锁根因。用户确认首扫未确认、后跟踪靠近一段又
逆时针转远，并描述“左右来回一段时间后，转远了”；原话完整保留，不改成整机成功。

**固定纸板短转诊断仍为INCOMPLETE。** `real_turn_probe_e5_01.jsonl`采用一次主机START、
真实蓝1/真实J3，无注入/heartbeat；pre三帧U57，START发送至STOP请求0.340987秒，
7个运动C快照均ALIGN逻辑(+4,−4)。这不是严格0.30秒机械脉冲，也不是实际UART波形捕获。
首先确认零速的FPGA timeUs=1542683620；之后实际新capture分别+245.133ms/U96锁定、
+525.021ms/U142未锁、+884.877ms/U169锁定，处理耗时约48–49ms。仅2/3符合锁定，
脚本输出INCOMPLETE、medianDeltaU=null、trend=UNAVAILABLE，未造三帧中值PASS。

后来`e5_turn_probe_settled.json`六帧U全173、健康锁定，但它们在首次零确认约90.489–
92.608秒后采集，不能证明1.5秒内停稳。用户确认纸板固定、最终车轮完全停止；对短促
启动后的尾转时长答复无法判断。固定目标U趋向并跨越中心支持方向正确且明显过冲；
200ms后新画面仍变化，机械停止时间/尾转原因未定，不能用zeroSent替代实物停稳。

**E6实现。** 在`motion_fsm.sv`、`member_c_control.sv`中，进入ALIGN时锁存方向/速度/
脉宽；误差abs(U−120)≤30且不在110–130死区时用3cm/s，>30用4cm/s，SEARCH仍4cm/s。
时长clamp(error×2000us,20000us,100000us)：U89为62ms/4、U90为60ms/3、U109/131为
22ms/3。更新U不延长同一脉冲；到期、跨侧、或转中后都先零速ACQUIRE，不直接反转/
平移。zeroSent后驻留1.5秒，再新fence及3个postfence新帧重新确认；900ms确认超时不变。
`memberCBoard.sv`生产默认同步1.5秒，build ID为E7070006；入ALIGN本来已居中且本次
未转动的路径才可APPROACH。LOST持续无目标仍按原300ms回SEARCH，不能说所有分支
均等待1.5秒；安全/IR/STOP/lease、累计搜索预算及120秒任务总限没有放宽或被短转重置。

1.5秒是保守设计配置，不是已证机械静止；3cm/s可靠起步尚未实测。更频繁的起步可能
放大前两圈已有单边前冲，不能只凭仿真宣布机械过冲/漂移已修好。源码正式冻结。

**E6聚焦结果与发布边界。** 正/负TURN_SIGN ModelSim各338检查、53完整UART PASS，
编译零错误零警告，编译加两次仿真5.2128905秒；日志`control_e6_20261104T144617Z/`。
覆盖短转到限、锁存不延期、3/4分档/完整±0.03左右字段、跨侧/转中先停、实际零包后
驻留与postfence三帧、SEARCH连续和原安全回归。测试驻留1500us是加速协议配置，
不当作生产1.5秒实测；正负各338不累加成676个独立需求。

像素链仅把center hold2帧延至4帧，总14帧、固定25fps，保留全部原12帧/顺序/像素输入/
断言，为新增停车边界提供真正三新帧，未降低资格。新副本单次PASS14帧/14报告、
sourceUnchanged=true，UART search41/left18/forward19/right34/zero178；编译9.217031秒、
仿真69.766992秒、包装器总78.991060秒，`pixel_uart_e6_20261104T144702_631205Z/result.json`。
上述简写均以`build/remaining_20261104/`为前缀，属于独立聚焦RTL_SIM。

正式E6 R6已完成一次**PASS：266.840318秒、13 PASS + 1 CAUGHT、targetMet=true、退出0**。
结果为`build/member_b/20261104T144856_668139Z_verilator_course/result.json`，61个新复制
源文件、cleanBuild=true、Verilator5.050、jobs4，满足285秒目标和300秒门槛；13个正式
bench（含14帧pixel、338项control、sonar代表）及原mutant检测保留，未借用旧二进制。
随后E6 Full Compilation的**编译工具退出0、1183.703秒，但整体验收FAIL、退出1**，
`build/member_b/20261104T144730_277631Z_build/result.json`记录critical timing warnings。
实际CLOCK_50 slow85 setup **−0.265ns/TNS −1.786ns**、slow0 **−0.203ns**，最差hold
+0.120ns。拟合为ALM29462/32070、寄存器41136、M10K357/397、DSP53/87、存储2802640bits、
PLL2。该构建在critical warnings门停止，没有独立timing_gate步骤或timing.json，不能记四角
门检PASS；器件装得下及功能仿真PASS均不能代替时序。E6失败产物**未下载、不得下载**，
当时设备仍E5 VISION_ONLY/未ARM/零速。没有随机换seed、放宽约束或忽略警告来接受产物。

### 2026-11-05：E6实际STA定位与E7等价运算修正

**先读取失败数据库的真实关键路径。** 对E6既有拟合数据库运行只读Quartus STA，目录
`build/remaining_20261104/e6_sta_diagnosis_20261104T150928_837210Z/`；耗时13.098885秒、
命令退出0，但结果明确`timingPass=false`，这是诊断完成，不是时序通过。两个slow角各20条
最差路径全部从mode[0]出发，到alignPulseUs低位寄存器：模式报告capture时间选择→adapter
afterFence减法/比较→centreU即时旁路→32位abs误差→串联两级DSP乘法→clamp→寄存器装载。
85°C最差路径15级逻辑、data delay19.971ns，两段DSP延迟3.159及2.047ns；完整报告为
`setup_6_slow_1100mv_85c_worst20.txt`、对应0°C文件及`path_endpoints.tsv`。
这才授权针对运算宽度修正，不绕开adapter的即时安全撤权或fence。

**E7只作等价算术优化。** `motion_fsm.sv`对五个默认参数（110/130死区、2000us/像素、
20000us最小、100000us最大）增加窄位路径：8位abs误差最大135，脉宽专用输入截到10..50，
用6位值扩成17位后计算`(x<<11)−(x<<5)−(x<<4)`，等于2000x。最大中间项102400在17位
范围内，减法非负；死区仍输出0，3/4速度分档使用未截限实际误差。非默认参数仍使用
原通用公式。build ID为E7070007；1.5秒、速度、TURN_SIGN、SEARCH、任务预算、IR/J3/
STOP等安全行为及SDC/QSF均未变。这不是新的机械调参，不能先声称已消除负setup。

**保留首次词法失败。** `control_e7_20261104T151306Z/`为COMPILE FAIL，ModelSim把
带基数十进制数字紧接三元`?`解析为不合法数字，5 errors/1 warning，仿真没有启动。
补必要空格后未改算术；原compile.log/result.json保留，没有用成功目录覆盖失败。
随后新目录`control_e7_20261104T151338Z/`编译0 error/0 warning，正/负TURN_SIGN各
338检查、53完整UART PASS（spin32/drive4/zero17，粗low24/high1、细low6/high1），
编译加两次仿真5.113292秒，result关联原失败目录。默认U0..255共256种输入与原公式
0处差异，`arithmetic_equivalence.json`保留每个U的原值/新值；枚举不是机械时间或STA证据。
上述简写控制目录均以`build/remaining_20261104/`为前缀。

**E7独立正式R6、构建、时序及实际下载均通过。** 本次R6结果为
`build/member_b/20261104T151442_166532Z_verilator_course/result.json`：**265.276162秒、
13 PASS + 1 CAUGHT、targetMet=true、退出0**；61个新复制源文件、cleanBuild=true、
Verilator5.050、jobs4，满足285秒目标及300秒门槛。含未改的14帧pixel、338项control及
真实时钟sonar代表；不另重复独立pixel，不沿用E6二进制或266.840318秒/R6 PASS。
Full Compilation目录`build/member_b/20261104T151422_461823Z_build/`的本版独立结果为
**PASS：编译1147.755秒、post-fit门检26.087秒，0 errors/92 warnings**。ALM29320/32070
（91%）、寄存器41015、M10K357/397、存储2802640bits、DSP51/87、PLL2；原始SOF位于该目录
`source/quartus/output_files/PartBDebug.sof`，6706155bytes。最差setup **+0.864ns（slow0）**、
hold **+0.117ns**；88项报告检查，Illegal Clocks及全部unconstrained均0。四角所需同步链
63/63、coverage PASS，MTBF验收NOT_ASSESSED；Gray9/9/32、相机/请求payload1590/22及
显示979物理端点覆盖完整。max-skew约束最差slack +18.437ns、net-delay约束slack +13.942ns，
是约束裕量，不是实际skew/延迟值。E7实际DSP回到51且setup为正，不借用E5/E6结果。

随后真实program成功，`build/remaining_20261104/program_e7_console.log`记录
programmerSucceeded=true、buildIdVerified=true、exit0，结束UTC2026-11-04 15:34:42.428181，
即2026-11-05 **02:34:42.428181 AEDT**；实际设计读回E7070007。下载后保持VISION_ONLY、
未ARM、左右0、zeroSent=true；用户蓝1仍在画外，塑胶地板及供电不变。

重新下载会清除运行时标定，因此随后明确恢复13.6秒经验扫描上限，而不是假定它跨下载保存。
`e7_scan_calibrated_13600ms.json`读回scanBudgetUs/remaining=13600000、CALIBRATED_TIME、
scanCalibrated=true、scanElapsed=0；REAL_CAMERA/蓝1稳定独热、sourceHealthyFresh=true、
targetObserved/Locked=false、VISION_ONLY/IDLE未ARM、左右0、zeroSent=true，IR=false、
sonarHold=false、真实J3694mm/valid MEASURED。没有START，不将参数恢复称为新一圈测试或
精确360°；该参数恢复阶段尚未开始真实搜索，后续observer01/02另列，分档短转的机械效果仍待验证。
E5真实任务失败及INCOMPLETE、三圈的超转/漂移/前冲，E6负setup和E7词法FAIL均继续保留；
3cm/s可靠起转、1.5秒机械停稳与真实视觉地面停靠仍未证实。

### E7首次真实观察未启动，保留INCOMPLETE

`build/remaining_20261104/integrated_blue1_e7_01.jsonl`在45秒实体POWER等待窗口内未观察到
ARM，含收尾147个CCTL快照全部IDLE/零速；结果**INCOMPLETE**，原因启动窗口到期并取消
迟到授权。首次ARM、首次任务终态和任务观察时长均null，完整窗口及收尾45.112171秒。
主机START/合成写入/heartbeat均0；到期STOP及切VISION_ONLY后仍未ARM、左右0、
zeroSent=true，cleanupErrors为空。此轮是**没有启动任务**，不是运动控制失败，更不是
搜索/停靠通过，也不据窗口内零速否认窗口外运动。用户随后明确报告反复按POWER无反应，
再按KEY0两次、每次短暂运动；此反馈与147个窗口内快照分别保留，触发因果未被完整捕获，
不推断是KEY0、迟到IR、视觉事件或其他某一因素已被证明。源码、构建及已下载E7不变。

随后主机设置并读回VISION_ONLY未ARM零速；`e7_after_key0_pairs.json`六组C/B分别冻结样本
确认B仍E7，5/6 C源健康，一次candidateOverflow/frameGood=false后恢复。J3依次92mm/HOLD、
792mm仍HOLD、788mm解除，之后789–792mm；此处本来零速，不能算运动急停验收。
KEY0把运行时扫描参数清为10秒/SCAN_UNCALIBRATED，符合复位设计。整理手部、线缆与红2后，
`e7_scan_restored_after_key0.json`明确恢复13.6秒/CALIBRATED_TIME、V1零速及J3737mm有效，
不是参数跨复位保存，也没有重新编译或下载。

### E7第二次真实任务：缠线/近距HOLD，观察到限后INCOMPLETE

`build/remaining_20261104/integrated_blue1_e7_02.jsonl`包含261个CCTL及258个BCTL快照。
首次ARM记录在主机20.0387466秒，任务观察60.0152787秒，含收尾80.0976572秒；结果
**INCOMPLETE**，原因为60秒任务观察限，firstTerminalSnapshot=null，不是DOCKED/NOT_FOUND。
主机START/合成写入/heartbeat均0，REAL_CAMERA/真实J3、13.6秒预算，首次SEARCH逻辑(+4,−4)。

轮询记录约20.039秒SEARCH（738mm）→21.331秒ACQUIRE（748mm）→23.701秒确认未成回SEARCH
（805mm）→26.068秒HOLD（215mm）→28.728秒解除HOLD回SEARCH（319mm）→29.598秒再次HOLD
（33mm）。累计SEARCH止于4.512126秒，未见ALIGN/APPROACH/DOCKED；最后收尾VISION_ONLY、
未ARM、左右0、zeroSent=true，J3251mm有效但HOLD仍在，cleanupErrors为空。轮询时刻不能
当作精确传感采样/状态转换或机械停车延迟，60秒是主机观察限而非生产120秒任务总限。

用户原话：“**扫过了蓝1，继续转的时候，遇到了线缆缠绕，然后超声波判定到距离过近中止**”。
保留线缆及近距保护对本次试验的影响，不将它归为纯控制逻辑失败或主任务成功；因未进入ALIGN，
本轮也不能证明新分档短转的实物效果。下一步等待用户把蓝1置于居中位置，做避免整圈缠线的
接近停靠验证；真实落地DOCKED和机械改善仍PENDING。源码与已通过的构建保持冻结。


## 2026-11-05: E7地面试验04/05、连续直行隔离与E8修复

E7构建/R6结果保持不变。窗口03再次45秒未ARM并正常收尾；用户报告多次POWER无反应，但无精确IR时刻，不能断言遥控器故障。随后经用户确认就绪，改用单次主机START，保留真实相机/J3/IR/UART、操作员A急停及限时STOP→VISION_ONLY，零合成视觉写入、零续租；这不作为POWER因果验证。

真实任务04从U112/J3约699mm开始，初始+5/+5后反复短转/驻留，60.1635664秒、206 C/201 B，未DOCKED；用户观察向前蠕动、左右累计约1/3.5cm。真实任务05从U197开始，15.048011秒、56 C/51 B，4cm/s短转把U带到123，随后APPROACH又使其到约56；用户观察主要左轮动作、右轮基本不动。两轮均INCOMPLETE并正常零速收尾，未以瞬间居中算停靠。

为了区分视觉切换与持续直行，两秒合成居中坐标经过真实C/超声/IR/串口和注入租约：+5/+5至J3<500mm后+3/+3，J3由618mm降至循环末454mm、零速后430mm，用户确认基本直着向前。此项仅证明该条件下连续前进可推进，不是实相机停靠，不能证明轮端同步或PID根因。

E7070008保留原110–130对准/停靠死区与全部安全资格，仅在已经进入APPROACH后允许U75–165内连续正向差速修正（远距5/3，近距4/3，方向随误差/原TURN_SIGN）；居中仍5/5或3/3。范围外或到350mm偏心时先ACQUIRE，完成零速、1.5秒保守驻留及新fence后三帧，再进行原短脉冲对准，避免前进后直接反转。SEARCH、累计预算、初始ALIGN、轮速极性、底盘固件及协议不改。E8独立仿真、构建、下载及首轮蓝1地面结果分别列于下文，未沿用E7 PASS。

Detailed raw paths, physical quotes and evidence boundaries are recorded in [REPAIR_RESULT](docs/REPAIR_RESULT.md). E8 now has one real-camera blue-1 approach/docking result from an initially locked target. Search from no target, five other bays and E8 POWER/red-2 starts remain pending. The earlier two-second centred injection remains synthetic vision through real hardware and is kept separate from the new camera result.


E8定向控制回归已实跑PASS：`build/remaining_20261104/control_e8_20261104T160731Z/`，两种TURN_SIGN各433检查/88条完整UART，compile+两sim共6.7496263秒、编译零错误零警告。新增真实编码5/3、4/3两方向，APPROACH范围/距离边界与立即撤权、退出后的零速/驻留/新fence三帧均覆盖。E8正式R6独立PASS：`20261104T160829_370108Z_verilator_course`，270.641086秒、13 PASS + CAUGHT、targetMet=true；14帧真实像素处理链至UART的右向纠偏实际为34条3/5前进差速、rightSpin0，保留帧数、识别和安全断言。

### E8完整构建、实际下载及蓝1真实落地DOCKED

本版`build/member_b/20261104T160829_127927Z_build/result.json`为PASS：compile1159.722秒、
post-fit25.963秒、0 errors/92 warnings；ALM29281/32070（91%）、寄存器41081、M10K357/397、
存储2802640bits、DSP51/87、PLL2，setup/hold最差+1.021/+0.121ns。88项报告检查、Illegal/
unconstrained全0；四角同步链63/63 coverage PASS，MTBF NOT_ASSESSED，不沿用E7结果。
原始`source/quartus/output_files/PartBDebug.sof`为6706156bytes。实际program于UTC
2026-11-04 16:28:58.446132（AEDT2026-11-05 **03:28:58.446132**）成功，E7070008读回匹配，
`program_e8_console.log`保留证据。发布`firmware/E7070008/PartBDebug.sof`（当时发布副本，后由E9替换）
与原产物逐字节一致；旧E7发布副本移除，原build/失败日志保留。下载后在V1零速明确恢复
13.6秒运行时参数，见`e8_scan_calibrated_13600ms.json`，不声称跨下载保存。

首次真实蓝1日志`build/remaining_20261104/integrated_blue1_e8_01.jsonl`输出
**DOCKED_OBSERVED**：116个C快照、110个不同B帧，B全部good且locked。真实相机/J3/IR/UART、
INTEGRATED，一次主机START，合成写入/heartbeat均0；起始蓝1已锁定，因此这次不覆盖SEARCH。
首次ARM主机2.169262秒，APPROACH(+5,+5)、J3690mm；随后462mm时(+3,+3)、365mm时采到
(+4,+3)差速，约6.076秒在350mm偏心处先ACQUIRE。之后约25.4秒末端微调，轮询采到3个
ALIGN(+3,−3)快照并多次静止重确认；采样数不是完整短脉冲次数，不能认定1.5秒机械停稳。

首次DOCKED主机31.484328秒，观察ARM到终态**29.315066秒**；未ARM、左右0、zeroSent=true、
J3 **329mm**，邻近独立B快照U110。12个DOCKED快照保持零速/未ARM，首末跨度**3.18423秒**，
随后finally STOP/VISION_ONLY，cleanupErrors为空；完整记录34.741535秒。C/B分别冻结，
不称同帧绑定；上述时间是主机观察时间，非精确物理停车或像素到UART延迟。
本轮未见SEARCH/LOST/HOLD/IR。用户原话：“**持续向前，不明显偏转，左轮大概多走了1cm？
探头前端距离大概33.5cm**”。这提供实际前进/停止位置观察；约1cm/33.5cm为估计，不能
把它与J3329mm的差值写成传感器校准或精密停车误差。

本轮实现了**已锁定蓝1起始的落地接近—减速—末端对准—DOCKED主功能**。约25秒末端微调
仍慢，重复性、左右位移差保留；蓝1阶段尚未覆盖其他牌/搜索/实体启动，后续证据分段追加。
此蓝1范围已随`8626c39`发布，后续为文档追加。生产源码保持冻结；E5/E7实测失败、E6时序失败
及此前不完整窗口均保留，不因单次蓝1完成而泛化全部需求通过。

### E8蓝2：连续日志内零速红2启动，与日志后人工前进观察分开

`build/remaining_20261104/integrated_blue2_e8_red2_01.jsonl`记录99C/96B、主机START/合成/
heartbeat均0，结果字段DOCKED_OBSERVED、cleanupErrors为空。真实红2event7→蓝2tag8到9→
新锁定→ARM确认，5个ARM的ACQUIRE快照后进入DOCKED；但**99个C快照全部L/R0且无permit**。
J3从前期约633mm在出牌/摆位中降到约295mm，ARM后292–303mm已在停靠距离内，因此这段是
静止启动链/近距完成，不能称移动接近停靠。原结果字段保留，解释不能由名称代替实物证据。

观察器结束后，用户另报最开始没动、按KEY0重置并将红2与红1重叠后向前走，最终约40cm且
可能受手/纸干扰。这段无连续日志，不能并入前述99个零速快照或补写运动时序/距离。
`e8_blue2_after_operator_key0.json`初读C为INTEGRATED/蓝2/DOCKED、未ARM零速zeroSent、
J3342mm有效、源健康/锁定、tag3；扫描10秒未标定符合KEY0复位。独立B仍E8，event7/id2、
蓝2U141、框144×159（预检87×97），good/observed/locked。事后框变大/近距不能单独区分
纸张与车体移动，U141不是DOCKED转换瞬间同帧证据；实际前进由用户观察支持。
之后V1/IDLE零速确认，`e8_scan_restored_after_blue2_key0.json`重新明确写回13.6秒。

结论保留为**红2板上授权链确认、人工实物前进观察加事后DOCKED佐证**，没有蓝1那样的
全程移动遥测，也不为补日志重复运行。蓝3POWER结果另列；源码、SOF及既有R6/构建数据不变。

### E8蓝3：实体POWER的完整真实移动任务通过

`build/remaining_20261104/integrated_blue3_e8_power_01.jsonl`为DOCKED_OBSERVED，257C/254B，
主机START/合成/HB均0。POWER后首次ARM61.5772666秒、DOCK77.3039882秒，相差**15.7267216秒**，
终态J3 **321mm**；11个DOCKED快照零速/未ARM保持3.127523秒，随后V1/IDLE零速收尾无错误。
完整含等候记录80.486497秒，不能把等候或轮询差换算成机械停车延迟。

APPROACH非零快照12个：5/5×2、3/5×4、3/4×6，J3从656经500降到334mm，约65.615秒入
ACQUIRE末端微调后完成停靠，无SEARCH。计数为C轮询状态，不是UART包数或实测轮速。
254B全good/fresh，无当前overflow/error，253锁定；唯一未锁为初始新tag ACQUIRING。
末B frame15822仍good/locked，U128、框152×169。清理C源健康暂false来自mode切V1的
tag7→8新请求重建，不称坏帧；终态未ARM、左右0、zeroSent=true。

用户原话：“**稳定向前，最终距离大概31cm**”。可计蓝3真实接近/差速减速/微调/DOCKED
及E8实体POWER启动通过；约310mm与板上321mm分开保留，不宣称精确误差或推断E7旧POWER
无响应根因。蓝4等摆位，蓝5/6和画外起始搜索仍待；只追加文档，源码/SOF/R6/构建不变。

蓝3收尾并非全程无sonarHold：约80.119秒J3167mm/hold=true，下一约80.431秒308mm/hold=false，
仍为DOCKED未ARM、左右0、zeroSent=true，未因距离恢复复驶。短近读数是否来自尺量/手部遮挡
未证实，不补猜原因；11个DOCKED样本的3.127523秒零速保持仍成立。

### E8蓝4完成真实停靠，保留抽动与轻微偏右

`build/remaining_20261104/integrated_blue4_e8_host_01.jsonl`：DOCKED_OBSERVED，99C/93B，
主机START1、合成/HB0。首次ARM2.1602634秒为ALIGN(−3,+3)/655mm；约7.300秒APPROACH5/5
（642mm）→8.043秒5/3（585mm）→9.260秒4/3（487mm）→11.206秒ACQUIRE零速（334mm）。
DOCK28.2996343秒、J3316mm，ARM至DOCK **26.1393709秒**；11个终态快照跨3.27686秒均
316mm、未ARM、左右0、zeroSent，末V1清理无错。记录全长31.642262秒，不当精确机械延迟。
93个不同B帧全good/fresh/observed/locked，无候选错误/overflow；框84×94→157×172，
U132→最低77→末111，无HOLD/IR/LOST/SEARCH。

用户原话：“**启动的时候有抽动，然后偏右。直着向前接近后。停止，最后短向左修，修回居中
（虽然还是有点偏右），最终停车距离大概32cm**”。据此真实蓝4接近/减速/微调/停靠通过，
但起步抽动、偏右、最终仍略偏右及约17.1秒末端微调保留，不写“偏航已消除”或实测轮速。
约320mm用户估计与板上316mm独立记录。蓝5准备中，蓝6计划画外起始搜索，尚无结果；
只更新现场文档，不变更E8源码、SOF或既有构建/R6。

**随后范围变更：**用户明确“**我觉得5/6都不用单独测了，1-4已经说明了性能**”。蓝5/6
独立落地计划已取消，本轮最后一次画外搜索改用蓝4；当前等摆位，完成后即文档/PDF/导出/
发布收尾，不继续逐牌扩测。六牌静态识别全覆盖仍是独立事实，蓝5/6无单独地面任务证据仍
作为限制保留，不把取消测试改写成测试PASS，也不把重复性等未覆盖项变成新的执行要求。

### 2026-11-05：E8蓝4画外搜索未完成，E9按新需求增加有限回扫

最后画外试验`build/remaining_20261104/integrated_blue4_e8_search_01.jsonl`已经实际运行，
结果**NOT_FOUND_OBSERVED / SCAN_BUDGET**，153 C / 150 B；真实相机、实体POWER，
主机START/合成写入/heartbeat均0。首次ARM22.954783秒，首次终态49.422059秒，
观察任务26.467304秒；总记录49.482598秒、cleanupErrors为空。许可搜索累计13.6秒，
含停车/HOLD的主机观察时长不当成连续旋转时长。

24.568753秒的C frame24263确实observed=true、locked=false，停止SEARCH(+4,−4)进入
ACQUIRE，zeroSent=true、累计1.586529秒；26.999764秒仍未取得新锁定而回SEARCH。
31.709532秒J3240mm进入HOLD，32.656468秒2163mm恢复；34.005920秒231mm再次HOLD。
用户移开障碍物后，41.016427秒4000/valid FAR恢复SEARCH；46.869438秒累计预算到限，
最后ACQUIRE仍未锁定，49.422059秒NOT_FOUND、未ARM/零速/zeroSent，J3297mm。
finally STOP/VISION_ONLY零速无清理错误；从未到ALIGN/APPROACH/DOCKED。

用户说扫过蓝4两次却未锁定，并问是否扫速太快。实际候选U约65→155→215→218与停车后
目标继续越过视野相容；150个B读回健康/新鲜、处理38.819–45.892ms，无新增drop证据。
不能据此唯一认定机械尾转原因，也不能拿稀疏B轮询漏掉首帧来否认C已observed；近障和
用户移障过程保留。这一失败不覆盖此前蓝1/3/4从已见目标起始的停靠成功，也未补成搜索PASS。

用户随后明确：“**如果是看到后，停转但是过了，我觉得可以加一个停转后慢速或小步回扫的功能**”。
采用E7070009定向回扫，未将全部SEARCH改为周期停转，也不调整原4cm/s搜索速度：

1. 只有正向SEARCH中本次目标observed触发的ACQUIRE授予资格。先完整零速UART、1.5秒
   保守驻留、新fence与三帧确认；确认超时且当前目标已不可见、来源健康、安全且预算未尽，
   才反向。普通ALIGN/APPROACH/LOST/HOLD的ACQUIRE不自动获得资格。
2. 每步最多**150000μs**、全任务最多**3步**，复用SEARCH与原motionApplied计时链；
   生产正常(+4,−4)、反扫(−4,+4)。反向仍收费到同一scanElapsedUs，余量不足即提前零速；
   不重新给一圈，不重置120秒总任务时间，后续再见牌也不能退还已经使用的尝试。
3. 每步到时、再次observed或预算耗尽均组合撤销输出，再完整ACQUIRE；新锁定才进原ALIGN。
   源失效/HOLD立即撤权且不退款；保留待停车确认标志，恢复后正向运动前仍须完整零UART、
   驻留、新fence与确认等待，避免通过HOLD/LOST绕过回扫后的停稳要求。
4. STOP、IR、选择/模式/raw改变、注入租约失效、reset及新任务清除旧授权；成功锁定撤销
   回扫资格但不返还本任务次数。参数0禁用，非法步数或脉宽关闭功能，2bit计数不环绕。
   现有APPROACH差速、ALIGN脉冲、J3/IR安全及三帧资格不放宽。

150ms是逻辑请求上限，非实测角度或轮端脉宽；1.5秒不是已证明的机械停稳上界。
反复起步仍可能不对称，且13.6秒预算包含反向后不能保证完整正向一圈。是否实际收回目标
仍须本版硬件证据，不能由代码或仿真提前宣布成功。

`build/remaining_20261104/control_e9_20261104T171519Z/`的聚焦ModelSim两种TURN_SIGN
各**696检查/245条完整UART PASS**，spin111/drive30/zero104，原双向细转及差速完整JSON
检查保留；编译加负/正两次仿真合计**20.8500433秒**，0 errors/0 warnings。覆盖150ms
到限/三次与第四拒绝/同预算截断、目标重获后三新帧、源/HOLD中断后的完整等待、七类取消
不复活。驻留/确认参数在TB缩短验证关系，回扫仍保留150ms，不当成机械测量。

首次宿主包装器漏掉实际`PASS:`的冒号而误记FAIL，保存`wrapper_result_initial.json`；
负sign真实仿真一次通过、**未重跑**，仅同库补跑尚未执行的正sign并纠正汇总。
`commands.json`及负/正原日志可追溯；无RTL失败被隐藏，也未重复计数。三文件已冻结、
独立只读审查通过，原14帧像素回归输入/断言保持。

20.8500433秒是上述编译和两次仿真调用的累计执行时间，未包括修正宿主匹配器的间隔。TB保留150000逻辑微秒门限，但共享timeUs每20 ns时钟递增1，UART和驻留均加速；这是逻辑/协议验证，不是板级150 ms管脚脉宽或机械停稳测量。

**当前E9状态：**正式R6的`build/member_b/20261104T171630_007376Z_verilator_course/result.json`
已独立**PASS，274.530007秒**，13 PASS + CAUGHT、cleanBuild=true、targetMet=true、退出0，
Verilator5.050、jobs4，满足285秒目标。原14帧像素输入/断言未改，本版控制696检查/245完整UART
也在本次真实Verilator仿真通过，未借用E8的270.641086秒结果。完整构建及post-fit目录
`build/member_b/20261104T171519_480274Z_build/`随后独立通过Full Compilation和post-fit，实际下载也已核对E9身份；画外蓝4实机已记录INCOMPLETE：60秒观察窗未DOCK、主机STOP收尾，且没有反向SEARCH，回扫物理效果未验证。E8的构建、下载和停靠通过只属于E8，不继承；蓝5/6单独落地取消范围保持。

### E9独立构建、实际下载与零速准备

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

### E14 candidate source publication / E14候选源码推送

按用户要求，编译进行时先推送当前冻结候选源码，后续实测结果可独立追加。README已合并成单个逐节中英对应文件，独立英文文件删除；保留15个主节、37个子节和原英文独有说明。发布白名单/fixture同步，submission14项(0.287s)、结构6项(2.038s)和实际60依赖/53bench结构检查PASS。当前仍是E14构建运行中、未下载；R6两轮FAIL如实保留。不发布未过时序的E14 SOF，不生成已验收最终ZIP。

At the user’s request, publish the frozen candidate sources during compilation; later hardware results may follow in another commit. One section-paired bilingual README retains15 main sections,37 subsections and all English-only content. The export/structure contract was updated;14 submission tests(0.287s),6 structure tests(2.038s) and the actual60-dependency/53-bench structural check passed. E14 compilation is still running and it is not programmed; both R6 failures remain recorded. No unqualified E14 SOF or validated final ZIP is published.

### E14完整构建与四角时序通过 / E14 full build and four-corner timing passed

**中文**

最终E14 `build/member_b/20261104T220114_044911Z_build/result.json`已 **PASS**：Full Compilation **1333.597秒**，独立post-fit门检 **25.925秒**，0 errors、93 warnings。四角最差setup **+1.136 ns**、hold **+0.118 ns**；reportGate检查88项、未约束项目全0。ALM **31016/32070（97%）**、41154寄存器、357/397 RAM、51/87 DSP、2 PLL。资源余量较小；同步链覆盖通过，但MTBF仍未评估。E13负裕量失败不被改写，这次E14自己的完整拟合/门检才提供时序通过证据。

[E14 SOF](firmware/E7070014/PartBDebug.sof)为成功build原始产物的逐字节副本，**6706155字节**，SHA256 `f74a3ff85a8543ac6a204d48d4a0a578189ca77a134c444a92d4a2c7920e5aba`。复制前执行当前源码/成功build绑定校验，未重新生成或改写SOF。E12副本保留为历史回滚；E14下载、板上身份及真实任务结果须另列，不因build通过自动成立。R6两轮失败保留，拟合结束后的fresh完整复跑与真实红2全流程仍待其自身结果；不生成“已完成整机验收”的ZIP。

**English**

Final E14 `build/member_b/20261104T220114_044911Z_build/result.json` is **PASS**: Full Compilation **1333.597 seconds**, independent post-fit gate **25.925 seconds**,0 errors and93 warnings. Across four corners, worst setup is **+1.136 ns**, hold **+0.118 ns**; reportGate evaluated88 checks with all unconstrained categories zero. Resources: **31016/32070 ALMs(97%)**,41154 registers,357/397 RAM blocks,51/87 DSPs and2 PLLs. Logic headroom is small; synchronizer coverage passed, while MTBF remains unassessed. E13's negative-slack failure is preserved; these are E14's own accepted fit/timing results.

The [E14 SOF](firmware/E7070014/PartBDebug.sof) byte-matches the successful original artifact: **6706155 bytes**, SHA256 `f74a3ff85a8543ac6a204d48d4a0a578189ca77a134c444a92d4a2c7920e5aba`. Current-source/successful-build binding was checked before copying; no SOF content was regenerated or modified. E12 remains a historical rollback copy. Programming, board identity and physical task results require separate evidence. Both failed R6 attempts remain; the fresh complete run after fitting and real red2 end-to-end task await their own results. No archive is labelled as fully hardware-accepted.

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

`integrated_blue4_e14_red2_search_to_dock_01.jsonl`保留 **728个C、91个B快照**，真实红2确认使请求tag4→5并ARM进入SEARCH；**host START、合成写入和heartbeat均0**。首次ARM后的观察 **60.0170459秒**，结果 **INCOMPLETE**、未DOCK。已采49个SEARCH运动快照，随后真实近障保护停车；没有采到ACQUIRE、ALIGN、APPROACH或DOCK。搜索命令累计 **6.552069秒**，J3从起步约725 mm进入近距，采到161 mm。最终观察窗到限后STOP→VISION_ONLY收尾，ARM0、左右0、zeroSent、J3 732 mm、HOLD=false，cleanupErrors为空。

用户反馈“超过蓝四没停车”。约38.08秒的一个B快照有蓝候选框x83..170/y48..119，却因reason4被拒绝；它不是接受的蓝4目标，且约1秒间隔的B采样不能证明所有中间帧或唯一失败原因。不能将本轮写成成功抓牌后跟踪、接近或自主停靠。真实红2到新请求/SEARCH链路和近障保护均有板上证据，但完整任务仍未通过。

独立静止policy实机写入 **50 px /1400 ms /360 mm /550 mm** 并读回，再恢复 **45/1500/350/500**，两次CLI exit0、维持零速。证据为`e14_policy_stationary_write.json`和`e14_policy_stationary_restore.json`。这证明四个新字段的板上写入/读回/恢复，不是这些参数的运动性能验收。主线继续在同一个E14 SOF内调参，结果分轮保留。

**English**

`integrated_blue4_e14_red2_search_to_dock_01.jsonl` retained **728 C and91 B snapshots**. A real red2 confirmation changed request tag4→5 and armed SEARCH, with **zero host START, synthetic writes or heartbeat commands**. The observation after first ARM lasted **60.0170459 seconds**, ending **INCOMPLETE**, without DOCKED. Forty-nine SEARCH motion snapshots were recorded before real close-obstacle protection stopped motion; no ACQUIRE,ALIGN,APPROACH or DOCK was sampled. Accumulated scan-command time was **6.552069 seconds**. J3 started around725 mm and later sampled161 mm. At the observation limit, STOP→VISION_ONLY cleanup ended disarmed,L0/R0,zeroSent,J3 732 mm,HOLD=false, with no cleanup errors.

The operator reported that the robot passed blue4 without stopping for it. One B snapshot around38.08 seconds contained a blue candidate atx83..170/y48..119 rejected withreason4. It was not an accepted blue4 target; roughly one-second B sampling cannot establish every intervening frame or a unique cause. This is not accepted-target tracking, approach or autonomous docking success. Real red2→new request→SEARCH and close-obstacle protection have board evidence; the complete task remains unpassed.

An independent stationary hardware policy write/readback changed all four fields to **50 px/1400 ms/360 mm/550 mm**, then restored **45/1500/350/500**. Both CLI calls exited0 and remained zero, recorded in `e14_policy_stationary_write.json` and `e14_policy_stationary_restore.json`. This verifies writing, reading and restoring the four fields, not their motion performance. Further tuning uses the same E14 SOF and retains each trial separately.
