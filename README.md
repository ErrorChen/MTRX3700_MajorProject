# ECHO-7 / MTRX3700：视觉引导车位搜索与停靠 / Visual bay search and docking

本文件是唯一维护的中英双语操作指南；每节按中文、English对应阅读。详细历史保留于[版本记录](VERSION_README.md)。

This is the single maintained bilingual operating guide. Each section pairs Chinese and English; detailed history remains in the [version record](VERSION_README.md).

**中文**

正式工程是 `quartus/PartBDebug.qpf`，顶层是 `echo7IntegratedTop`，器件是 DE1-SoC 的 Cyclone V `5CSEMA5F31C6`。同一个 SOF 提供真实视觉调试、合成视觉底盘调试和整机运行。目标只能由实体 SW0–SW5 选择；JTAG 不提供直接轮速或假超声距离入口。

本次构建、下载和实机测试的具体结果见 [本次修复验收记录](docs/REPAIR_RESULT.md)。旧版本的拟合、仿真和实拍记录保留其历史含义，不代表当前代码已经完成实车验收。原始来源与成员归属见 [OWNERS.md](OWNERS.md)。麦克风和语音识别已取消。红1保留自动校色；按本次追加需求，红2在非活动任务时重新读取当前实体拨码、重锁并请求启动。

**English**

The production project is `quartus/PartBDebug.qpf`, with top level `echo7IntegratedTop`, targeting the DE1-SoC Cyclone V `5CSEMA5F31C6`. One SOF supports real-camera vision debugging, chassis debugging with synthetic vision, and integrated operation. Only physical SW0–SW5 select the target. JTAG cannot directly set wheel speeds or inject a fake ultrasonic distance.

Build, programming and board-test results are recorded in the [repair acceptance record](docs/REPAIR_RESULT.md). Earlier fit, simulation and camera records retain their historical scope; they do not certify current code on the vehicle. Sources and member attribution are in [OWNERS.md](OWNERS.md). Microphone and speech recognition have been removed. Red1 retains automatic colour calibration. Following the user's additional requirement, a newly presented red2 reselects the physical switch target, reacquires it and requests a start when no task is active.

## 导航 / Contents

- [E14 最终源码与当前交付状态 / E14 final source and delivery status](#current)
- [E12 与较早版本的历史验收范围 / Historical E12 and earlier acceptance scope](#history)
- [环境与硬件前提 / Environment and hardware prerequisites](#environment)
- [开关、按键与显示 / Switches, buttons and displays](#controls)
- [红1校色与视觉诊断 / Red1 calibration and vision diagnostics](#vision)
- [三种模式 / Three operating modes](#modes)
- [可运行命令 / Executable commands](#commands)
- [E11：停车状态下的小范围调参 / E11: bounded parameter tuning while stopped](#tuning)
- [E12：独立设置ALIGN总时长与起步段 / E12: independent ALIGN duration and startup stage](#pulse)
- [搜索、对准、停车与恢复 / Search, alignment, docking and recovery](#navigation)
- [三阶段操作 / Three-stage reproduction procedure](#procedure)
- [构建与验证 / Build and verification](#build)
- [按版本区分的实机证据 / Version-specific hardware evidence](#hardware)
- [已知限制与未验证范围 / Known limitations and unverified scope](#limitations)
- [管脚与文件 / Pins, files and ownership](#files)

<a id="current"></a>

## E14 最终源码与当前交付状态 / E14 final source and delivery status

**中文**

当前开发源码为 **E7070014（最终迭代候选）**，完整构建、时序、R6及实机全流程仍待本轮完成。当前已经发布且最后确认在板运行的是 **E7070012**。**E7070013 的定向仿真和 R6 通过，但 Full Compilation 的时序检查失败，未下载、未实机测试，不能使用其 SOF。** 以下 E12 及更早结果均属于各自历史版本，不能升级为 E14 的成绩。

E14 将用户同意的最多 200 ms 有限短转继续、最终启动配置、底盘自动反馈初始化、UART 字符查表时序修正和停车调参合并。主要验收仍是一次真实、连续的 **实体拨码选择 → 新呈现红2 → 自动搜索 → 停稳确认/跟踪 → 接近 → 自主 DOCKED 停车**，以及真实 J3 近障保护和 IR A 急停。主机观察到时限后发送 STOP 不算自主停靠；各段独立成功不能拼成完整任务。

**English**

Current development sources are **E7070014, the final iteration candidate**. Its full build, timing, R6 and complete hardware flow are still pending this run. **E7070012 remains the published and last confirmed programmed image. E7070013 passed focused simulation and R6 but failed Full Compilation timing; it was never programmed or physically tested. Do not use its SOF.** E12 and earlier results below retain their original version scope.

E14 combines the approved at-most-200 ms turn continuity rule, startup profile, chassis telemetry initialization, UART ASCII lookup timing repair and stationary tuning. Main acceptance is one real uninterrupted **physical switches → newly presented red2 → automatic search → stopped confirmation/tracking → approach → autonomous DOCKED stop**, plus real J3 near-obstacle and IR A protection. Host STOP at an observation deadline is not autonomous docking; independent successful segments do not form a complete task.

### E14 启动、红2与安全行为 / E14 startup, red2 and safety behavior

**中文**

- 上电/KEY0 后为 INTEGRATED、未授权、零速。先完成一条零速运动 JSON，再在真实未 ARM、零速且 UART 空闲时发送一次 `{"T":131,"cmd":0}`，关闭 UGV 的 RAM 自动反馈。`chassisInitSent` 只表示本地完整发完最后换行字节，不是底盘执行 ACK；初始化未完成前不接受新运动任务，早按的启动不排队重放。
- KEY0 不截断正在发送的 UART 行；复位事件重新安排完整零速和初始化。若只重启底盘，待底盘启动后按 KEY0 重新初始化；系统不能自动检测所有底盘单独重启。FPGA 断电后仍须重新下载 SOF，T131 不是永久固件设置。
- 红1负责校色，蓝1–6才是车位。红2只重新读取当前合法实体选择并请求新任务，不替代拨码。复位/初始化等边界中已经留在画面内的红2不会自动启动：先移开，连续三个健康帧确认缺失，再新呈现并确认。活动任务中的红2不重复启动。
- E14 启动配置是已尝试的 E12 地面配置：search/turn/approach/fine/tolerance = **3/4/5/4/30**；短转 **200/200/60/6**（最短/最长/kick 毫秒/kick cm/s）；存储扫描预算 **15.1 s**。这是塑胶地板、历史供电/载荷条件的近似时间配置，并非新 E14 三次精确 360° 标定，也不是实验室环氧树脂地板标定。它基于两次单圈与一次双圈归一化参考，且早于关闭自动反馈；改变 search 仍使扫描资格失效。
- 仅已锁定且原定时长不超过 **200 ms** 的原地短转，可在健康短暂未识别/同身份重新获取时完成原剩余时长，不延长、重起 kick 或改向。可信坐标越过允许居中边界可提前停；坏帧、过期、错误选择/身份、歧义、近障和 A 仍立即停止。配置超过 200 ms 时保持原持续锁定要求。前进失锁仍立即停车，随后零速驻留和新三帧确认。
- **≤250 mm 的近障 HOLD 和连续三个新鲜 ≥300 mm 读数的释放规则固定**，与下面可调的正常停靠距离分离。A 是锁存急停；第一次新 POWER 只解除锁存，仍停车。DOCKED/NOT_FOUND 后退远障碍物不会自动重启。正常结束的超量程回波显示 FAr；异常/过期测距仍保护。

**English**

- Boot/KEY0 starts INTEGRATED, disarmed and zero. After completing a full zero-speed motion JSON, the truly disarmed, zero, idle serializer sends `{"T":131,"cmd":0}` once to disable UGV RAM automatic telemetry. `chassisInitSent` means the local final newline byte has completed, not a chassis execution ACK. New tasks are gated until initialization completes; early starts are discarded rather than queued.
- KEY0 does not truncate an in-flight UART line; it schedules a new complete zero/configuration sequence. After a chassis-only reboot, wait for chassis startup then press KEY0. The design does not detect every chassis-only reboot automatically. FPGA power loss still requires SOF programming. T131 is not persistent firmware configuration.
- Red1 calibrates colour, blue1–6 identify bays, and red2 rereads the valid physical selection and requests a new task. A red2 left visible across reset/initialization cannot automatically start: remove it for three healthy absence frames, then present it anew for confirmation. It does not restart an active task.
- Production boot uses the tried E12 profile: search/turn/approach/fine/tolerance **3/4/5/4/30**, ALIGN **200/200/60/6** (minimum/maximum/kick ms/kick cm/s), stored scan budget **15.1 s**. This is a historical approximate plastic-floor time profile for the tested supply/load, not three new E14 precise 360-degree trials or an epoxy-floor calibration. Its basis is two single circles plus one normalized double-circle reference, measured before feedback shutdown. Changing search speed still invalidates scan qualification.
- Only an already locked original turn with total duration **≤200 ms** may finish its remaining time through healthy temporary not-found/same-identity reacquisition. No extension, re-kick or reversal is allowed. A trusted crossing can stop early; bad/stale/ambiguous input, wrong selection/identity, close obstacles and A still stop immediately. Longer configured turns retain continuous-lock requirements. APPROACH target loss still stops immediately, followed by zero dwell and three new confirmation frames.
- The **≤250 mm obstacle HOLD and three fresh ≥300 mm readings for release remain fixed**, independently of adjustable normal docking distance. A latches an emergency stop; the first fresh POWER only clears that latch and leaves the robot stopped. Retreating an obstacle after DOCKED/NOT_FOUND cannot restart the task. A normally completed out-of-range echo reports FAr; abnormal/stale ranging remains protected.

### E14 停车调参：同一 SOF 内设置 / E14 stationary tuning in the same SOF

**中文**

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

**English**

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

### E14 已完成的定向验证（尚非整板或实机验收） / Completed focused E14 checks (not full-build or hardware acceptance)

**中文**

冻结源码的定向结果 `motion_policy_20261104T220025097074Z/result.json` 为PASS、18.9839668秒：四字段策略覆盖11616种合法组合、11687项检查；debug251项；真实adapter/control基线2049项及500条完整UART；初始化启动门47项。随后 `motion_policy_20261104T220112003036Z/result.json` 的最终debug254项另覆盖生产启动值与KEY0恢复。主机工具31项、HOST_RUNNER18项通过。正式R6已扩为17个正常场景加mutant，正在独立执行；最终Quartus时序与实机仍待，不以定向结果替代。

**English**

The frozen-source focused result `motion_policy_20261104T220025097074Z/result.json` passed in18.9839668 seconds:11616 legal policy combinations and11687 assertions,251 debug checks,2049 real adapter/control checks with500 complete UART lines, and47 initialization-start gate checks. The subsequent `motion_policy_20261104T220112003036Z/result.json` passed254 final debug checks including production boot values and KEY0 restoration. Host tools passed31 tests and HOST_RUNNER passed18. Formal R6 now includes17 normal scenarios plus the mutant and is running independently. Final Quartus timing and physical acceptance remain pending.

### E14 正式R6首轮：Verilator工具崩溃，保留FAIL / First formal E14 R6: Verilator tool crash, FAIL retained

**中文**

`build/member_b/20261104T220131_947405Z_verilator_course/result.json`为 **FAIL，104.45794秒、exit1、targetMet=false**。失败点是新增`tb_chassis_init`的Verilator编译阶段：0.095982秒返回3221225477（Windows **0xC0000005**访问冲突），不是该测试的运行时断言失败，也不是完整套件耗尽时间。日志的通用错误文本包含“compilation failed or exceeded deadline”，但该次返回码/用时支持前者。原始FAIL与日志保留，不能因为不足285秒就称达标。

后续仅作等价测试台兼容修正，保留初始化场景及断言，生产RTL不改；最终完整fresh R6仍须重新执行并独立记录。Quartus E14完整编译继续，不能从该仿真工具崩溃推断FPGA时序或实机结果。

**English**

`build/member_b/20261104T220131_947405Z_verilator_course/result.json` is **FAIL,104.45794 seconds,exit1,targetMet=false**. Verilator compiling new `tb_chassis_init` returned3221225477 (Windows **0xC0000005**, access violation) after0.095982 seconds. This was not a runtime assertion failure or an exhausted suite deadline. The generic error text says compilation failed or exceeded the deadline; this return code and duration establish the compile failure. The original FAIL/logs remain and being below285 seconds does not make it a passing result.

Only equivalent testbench compatibility changes are planned, retaining initialization scenarios/assertions and unchanged production RTL. A fresh complete R6 still needs its own result. The E14 Quartus build continues independently; this simulator crash does not determine FPGA timing or physical behavior.

### E14 R6工具兼容修正与第二轮整体超时 / E14 R6 tool compatibility fix and second-run overall timeout

**中文**

首轮崩溃后，仅把`tests/member_c/tb_chassis_init.sv`内两处层次枚举引用`dut.SEND`/`dut.LOAD_FB`改为相同编码的本地常量；生产RTL、初始化场景及断言未削减。独立Verilator验证 `verilator_init_verified_20261104T220628_233730Z/result.json` 已PASS：4939项检查、183条完整UART、41条初始化报文及32768个ASCII等价组合，约8.21秒。它仅验证兼容修正后的初始化场景，不替代完整R6。

第二轮fresh R6 `build/member_b/20261104T220649_240451Z_verilator_course/result.json`仍为 **FAIL，301.821791秒、exit1、targetMet=false**。已完成10项PASS，包括全部新增场景、debug/red2和continuous；`perceptionCoreOverload_tb`运行时触及整个套件300秒时限而终止，后续场景未完成。不能写成17项PASS或285秒达标，且前两轮失败均保留。

该轮与Quartus拟合并行；主机争用是待核对的耗时因素，不是已确认唯一原因。计划拟合结束后、生产源码不变时重新执行完整fresh R6，再独立记录实际总耗时。未删除负载场景、未降低帧数/断言、未改285秒目标，也不跨运行复用旧二进制冒充clean build。E14仍未下载。

**English**

After the first crash, only two hierarchical enum references, `dut.SEND`/`dut.LOAD_FB` in `tests/member_c/tb_chassis_init.sv`, were replaced with same-encoding local constants. Production RTL, initialization cases and assertions were unchanged. Independent Verilator validation `verilator_init_verified_20261104T220628_233730Z/result.json` passed4939 checks,183 complete UART lines,41 initialization lines and32768 ASCII-equivalence combinations in about8.21 seconds. This validates the repaired scenario, not complete R6.

The second fresh R6, `build/member_b/20261104T220649_240451Z_verilator_course/result.json`, is **FAIL,301.821791 seconds,exit1,targetMet=false**. Ten scenarios completed PASS, including all new scenarios, debug/red2 and continuous operation. `perceptionCoreOverload_tb` was terminated at the whole-suite300-second deadline; later scenarios did not complete. This is neither17 PASS nor a met285-second target. Both failed runs remain preserved.

This run overlapped Quartus fitting. Host contention is a timing factor to investigate, not an established sole cause. The plan is another complete fresh R6 after fitting, with unchanged production sources and a separately recorded duration. No overload case, frame count or assertion is removed, the285-second target remains, and old cross-run binaries are not reused as a clean build. E14 is not yet programmed.

<a id="history"></a>

## E12 与较早版本的历史验收范围 / Historical E12 and earlier acceptance scope

**中文**

截至下述E12历史轮次，发布版本为 **E7070012**；该轮只补充同SOF/同参数的实机记录，没有新RTL、编译或R6。原正式R6 **223.404755秒（13 PASS＋CAUGHT）**、Full Compilation1163.903秒＋post-fit26.783秒、下载及静止pulse读写证据保留。此前第七轮从约41 cm重新POWER的独立任务达到DOCKED，J3 292 mm与探头前端尺量约370 mm差异未定；它不能替代60 cm或画外搜索闭环。其余真实搜索失败、左右起步/过冲问题仍按轮次记录。

后续OLED确认UGV Rover/version0.9，同E12重下载并恢复实验tune3/4/5/4/30、pulse200/200/60/6及15.1秒基准。T131仅关闭底盘RAM自动反馈，独立零速RX由约11 kB/s变为五样本0新增。连续改值trial1因真实500 mm诊断边界提前结束且没有物理验收；trial2已观察5/5→5/4→5/5三段，用户确认较快→较慢→较快→停车。单次ALIGN→完整零速驻留→APPROACH隔离也取得逻辑证据，用户确认“两侧轮子都一起走的”。这些是限定试验结果，不是精确轮速、直行精度或flowoff因果修复证明。

紧接着的一轮**真实相机画外搜索仍INCOMPLETE，60.0067485秒未DOCK**，由观察窗结束后的host STOP收尾；729 C/90 B、host START/合成写入/heartbeat均0。用户看到找到蓝4后反复修正、牌先到右边再到左边、最后居中，末段两轮共同前进后停；是否又发生大幅末段纠偏不确定。用户尺量**相机到标牌垂直距离46 cm**，板上J3末读数**407 mm**，测量起点不同，不能计算为同基准误差。收尾V1未ARM、permit0、左右0、zeroSent、IR0/HOLD0且cleanup无错误。实验组合仍不是推荐设置；完整搜索停靠未通过，原因未证实。SOF复位默认未改，不新增E13初始化或重复搜索结论。

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
| E7070011，历史已下载版本 | 停车V1五项调参；LOST必经完整ACQUIRE，确认义务跨HOLD/源失效 | runtime两sign各996/358、legacy847/289；首R6 FAIL302.015209保留，最终fresh R6 PASS219.199994秒/13 PASS＋CAUGHT。Full Compilation1375.853秒＋门检26.278秒PASS、实际下载和停车调参PASS；首轮/search3搜索NOT_FOUND，turn3/turn5均INCOMPLETE；最终3/5/4/3/40对照仍INCOMPLETE，降速未消除抽动/过冲；停止追加测试 |
| E7070012，当前发布 | ALIGN独立总时长与可关闭起步段，V1停车原子调参/独立读回 | 协议/控制/R6首跑223.404755秒/完整构建及实际下载PASS；真实静止调参PASS。前三轮INCOMPLETE，第四仅有限回正诊断通过用户观察，第五60.0399573秒INCOMPLETE/近障HOLD；未DOCK，第六轮tol30连续差速接近获用户确认，首次LOST即诊断STOP；第七轮约41 cm独立任务DOCKED，J3292/用户尺量约370 mm分别保留；第八轮画外搜索发现/恢复后仍INCOMPLETE60.1513566秒；第九轮turn4有限回正获反馈、首次APPROACH即STOP；第十轮完整搜索INCOMPLETE60.0024068秒；5/5逻辑请求不证明物理直行 |

已经完成真实硬件纠正及历史search4参数下塑胶地面的三次整圈观察，但六车位落地闭环和精确360°扫描尚未验收。早期实机主要在底盘架空条件下完成，后续地面记录另行标明；本README把现有实现、对应版本的实际证据和后续操作分别说明。后续复现实验的操作步骤也不代表已执行结果。

E5按新的实物反馈及用户要求，将生产`TURN_SIGN`改为−1，并把正常结束的超量程ECHO发布为FAR，保留信号异常保护。生产负号配置控制269检查、原12帧像素→UART及超声完整引脚专项46检查已分别通过。E5完整编译 **1173.143秒PASS**、post-fit门检 **25.799秒PASS**；最终R6 **239.403059秒PASS**，实际下载及E7070005读回通过。已取得的FAR/视觉零速实机结果与尚未完成的地面任务分别列出，首轮R6失败保留。

**English**

The current release remains **E7070012**. This batch adds physical evidence using the same SOF and settings, with no new RTL, compilation or R6. Original formal R6 **223.404755 seconds (13 PASS plus CAUGHT)**, Full Compilation1163.903 seconds/post-fit26.783 seconds, programming and stationary pulse readback retain their scope. The earlier independent trial seven restarted from approximately41 cm and reached DOCKED, but J3292 mm versus probe-front ruler approximately370 mm remains unresolved; it does not replace uninterrupted60 cm or outside-view search-to-dock acceptance. Other search failures, uneven starts and overshoot remain recorded by trial.

The startup OLED subsequently confirmed UGV Rover/version0.9. The same E12 was reprogrammed and experimental tune3/4/5/4/30, pulse200/200/60/6 and the15.1-second basis restored. T131 disabled only chassis RAM automatic feedback, with independent stopped RX windows changing from approximately11 kB/s to no increments in five samples. Command-change trial1 ended early at the real500 mm diagnostic boundary without physical acceptance. Trial2 retained5/5→5/4→5/5 holds and user-confirmed faster→slower→faster→stopped motion. A single ALIGN→complete zero dwell→APPROACH isolation also retained logical evidence, with the user confirming both wheels moving together. These are bounded results, not exact wheel-speed/straightness verification or a causal flow-off repair.

The subsequent **real-camera outside-view search remained INCOMPLETE after60.0067485 seconds, without DOCKED**, followed by host STOP at the observation limit. It retained729 C/90 B, with zero host START/synthetic/heartbeat commands. The user saw discovery followed by repeated corrections, the marker reaching the right then left side and finally appearing centred, with both wheels advancing together at the end before stopping. The user was uncertain whether another large final correction occurred. The measured **perpendicular camera-to-marker distance was46 cm**, while final J3 was **407 mm**; these have different origins and are not a same-baseline error calculation. Cleanup left V1/disarmed/no permit, both requests0, zeroSent, IR0/HOLD0 and no errors. This experimental combination remains unvalidated as a recommendation; full search-to-dock has not passed and causality is unconfirmed. Reset defaults are unchanged, with no E13 initialization or repeated-search result implied.

Historical published **E7070011** ended that run in VISION_ONLY, disarmed and zero-speed. Its firmware defaults and final experimental session settings are recorded separately. E11 adds stationary tuning and complete stopped reconfirmation after tracking loss. Focused runtime control passed 996 checks/358 complete UART messages for each TURN_SIGN, with 847/289 for legacy parameters. The first formal R6 timed out at 302.015209 seconds and remains FAIL; a fresh second run after scheduling optimization **passed in 219.199994 seconds with 13 PASS plus CAUGHT and targetMet=true**. Full Compilation 1375.853 seconds/post-fit 26.278 seconds passed at setup/hold +0.237/+0.120 ns, followed by verified E11 programming. Physical stationary parameter writes/independent readback, search-change calibration invalidation and default restoration passed. The initial stationary tuning sequence did not move; later ground trials ended NOT_FOUND at the original and search3 settings, while turn3 isolation only twitched and remained INCOMPLETE. E11 RTL was unchanged during those trials; the final experimental values were 3/5/4/3/40 with 15.1 seconds; turn5 ended INCOMPLETE and approach4 also ended INCOMPLETE, with twitching/overshoot unresolved. That round concluded at this experimental combination, without claiming measured speed accuracy or docking.

Historical **E7070010** had its own build, programming and publication, ending the physical trial in VISION_ONLY, disarmed and zero-speed. Following the user's acceptance of a wider centring tolerance, E10 defaults to U90–150 (±30 around 120). Beyond 350 mm, a fresh locked target within U75–165 may enter APPROACH directly at START or after complete ACQUIRE confirmation, reducing unnecessary stopped pivot alignment. E10 focused regression passed: default negative/positive TURN_SIGN each 804 checks/275 UART messages and legacy strict-band compatibility 817/278, in 29.1663517 seconds total. Formal R6 independently passed in 271.31444 seconds, 13 PASS plus CAUGHT, meeting 285 seconds. Full Compilation 1260.493 seconds and post-fit 25.832 seconds independently passed, with worst setup/hold +0.909/+0.118 ns. Actual programming and E10 identity verification passed; stationary calibrated blue4 preflight locked 4/4. The physical trial found and locked out-of-view blue4, briefly entered APPROACH, then lost the target and resumed SEARCH. It ended **NOT_FOUND/SCAN_BUDGET** after approximately 22.21 seconds of task observation, with no DOCKED or reverse SEARCH. The user confirmed the fixed target and stopped wheels; out-of-view search-to-dock remains unsuccessful. Independent E9 and earlier evidence follows.

Historical **E7070009** was built, programmed and published with the CCTL interface identifier **E7070001**; E11 now uses its actual BUILD_ID. Both TURN_SIGN configurations passed 696 checks and 245 complete UART messages each. E9 independently passed formal R6 in **274.530007 seconds, 13 PASS plus CAUGHT, targetMet=true**. Full Compilation **passed in 1218.109 seconds**, followed by a **26.779-second passing post-fit gate**: 29699/32070 ALMs (93%), worst setup **+0.629 ns**, hold **+0.117 ns**, and zero unconstrained items. The original E9 SOF was programmed and its identity verified. Four post-programming blue4 preflight pairs were healthy and locked at approximately 663–664 mm, with colour calibration and zero speed confirmed. The initially-out-of-view blue4 trial is **INCOMPLETE**: search found and locked the target, but repeated alignment did not reach DOCKED within the 60-second observation window. Host STOP then returned to zero-speed VISION_ONLY. No reverse SEARCH occurred, so physical reverse recovery was not exercised. E9 remains a historical release with its version-specific build and failure records retained.

E8 retains independent physical evidence: blue1, blue3 and blue4 approached and docked from already visible targets, with first observed ARM-to-DOCKED intervals of 29.315066, 15.726722 and 26.139371 seconds and terminal J3 readings of 329, 321 and 316 mm. Blue1/4 used one host START; blue3 used physical POWER. The user confirmed forward travel and stopping, while blue1/4 retained roughly 25/17-second final correction and blue4 retained startup jerk, rightward drift and a slightly rightward endpoint. Blue2 has separately scoped red2-chain evidence, out-of-window physical feedback and a later terminal state, without a complete motion trace. The user cancelled separate blue5/6 floor tasks; six-card static coverage does not establish their ground-task results.

E8's final initially-out-of-view blue4 search passed the card twice without sustained locking. After near-range interruption and the user's removal of an obstruction, it exhausted the 13.6-second budget, entered NOT_FOUND and stopped automatically. E9 implements the requested bounded reverse steps after a sighting is lost during stopped confirmation. That E8 failure is retained, along with E6's timing failure and E5/E7's physical failures. See the [version history](VERSION_README.md) and [repair record](docs/REPAIR_RESULT.md) for commands, measurements and evidence.

| Version | Main change in that version | Evidence obtained |
|---|---|---|
| E7070002 | Three modes, physical one-hot selection, red2 events, the complete safety chain and paged vision diagnostics | Full Compilation and R6 passed; board injection, wheel movement, IR and real blue1 tracking passed. A later single-frame overflow exposed a permanent C inhibit caused by historical fault state. |
| E7070003 | Separate recoverable bad frames from historical fault bits; establish a recovery fence at reception time | 236 control checks, R6 and Full Compilation passed. The board recovered healthy tracking with faultFlags=3 retained; 22 locks across 23 distinct real frames. A red2 start occurring before a new lock was then found. |
| E7070004 | Without scan calibration, a pending red2 start waits for the new request's three-frame target lock | **254 targeted checks PASS; formal R6 completed in 219.556074 seconds with all 12 items and CAUGHT passing; Full Compilation and actual programming PASS; the user physically confirmed red2 starting and stopping when blue1 left the view.** The host's two-second STOP was not independently timed at the wheels. Final state: VISION_ONLY, disarmed, logical zero speed, and the user confirmed standstill. |
| E7070005 | Production turn sign −1; completed over-range ECHO produces FAR while signal faults retain protection | **Formal R6: 239.403059 seconds, all 13 items plus CAUGHT PASS; Full Compilation and actual programming PASS.** Zero-speed blue1 health/lock 8/8; real open-space FAR 6/6, with the user confirming ` FAr` on the distance page. Ground-revolution observations 3/3; 13.6-second approximate scan budget configured; the release SOF has been copied. |
| E7070006, unprogrammed historical revision | Short ALIGN pulses and 3/4 cm/s speed tiers based on U error, then longer stationary dwell and fresh-frame confirmation | Both TURN_SIGN control configurations passed 338 checks/53 complete UART messages each, and the 14-frame fixed-25-fps pixel→UART test passed. The same source passed formal R6 in **266.840318 seconds, 13 PASS plus CAUGHT**. First Full Compilation acceptance **FAIL** for negative setup slack; no programming/hardware verification. The 1.5-second dwell is not a measured settling time. |
| E7070007, historical programmed version | Numerically equivalent narrower default pulse-width calculation for the actual STA path | All 256 U values equivalent; both TURN_SIGN configurations passed 338 checks/53 complete UART messages. Formal R6: **265.276162 seconds, 13 PASS plus CAUGHT**. Full Compilation/post-fit and programming/readback PASS; real blue1 trials 01–05 did not dock and retained asymmetric short movements/overshoot. Continuous-straight isolation produced actual forward travel that was basically straight. |
| E7070008, historical verified version | Once already in APPROACH, continuous forward 5/3 or 4/3 cm/s correction within U75–165; outside it or near the target while off-centre, complete a stop and reconfirm before pivoting | Both TURN_SIGN configurations passed 433 checks/88 complete UART messages; formal R6 passed in **270.641086 seconds, 13 PASS plus CAUGHT**. The 14-frame pixel→UART path verified forward-right 3/5 correction. Full Compilation/post-fit and actual programming/readback PASS; zero-speed blue1 preflight locked 4/4. A real blue1 task recorded board-level DOCKED and zero-speed dwell; the user confirmed continuous forward travel without obvious veering and approximately 335 mm from the probe front at the endpoint. Blue3 recorded physical POWER start and real approach/slowing/correction/docking, with the user confirming steady travel and an approximately 31 cm endpoint. Blue4 recorded real approach/docking from a pre-locked target, retaining startup jerk/rightward drift and slow final correction; a separate initially-out-of-view search ended NOT_FOUND and did not pass the search-to-dock requirement. Blue2 separately has a red2 chain, out-of-window physical feedback and a later terminal state, without a complete motion record; the user cancelled separate blue5/6 ground trials in this run. |
| E7070009, historical published version | Bounded reverse steps after a forward SEARCH sighting followed by stopped-confirmation timeout with the target absent; each step stops and reconfirms | 4 cm/s, 150 ms, at most three steps per task, sharing the original scan budget and task timer. Both TURN_SIGN configurations passed 696 checks/245 UART messages. Formal R6 independently passed in 274.530007 seconds, 13 PASS plus CAUGHT. Full Compilation 1218.109 seconds + post-fit 26.779 seconds PASS; programming/identity verification PASS. Physical search-to-dock INCOMPLETE: discovery/lock followed by repeated alignment, no DOCKED within the 60-second observation window, then host STOP/zero; no reverse SEARCH occurred, so physical reverse recovery remains unverified |
| E7070010, historical published version | Default centred band U90–150; beyond 350 mm a fresh lock within U75–165 can enter APPROACH directly at START/after complete ACQUIRE | Focused PASS: default both signs 804/275 each, legacy strict band 817/278, 29.1663517 seconds. Formal R6 independently PASS271.31444 seconds, 13 PASS plus CAUGHT; Full Compilation 1260.493 seconds/post-fit 25.832 seconds PASS; 6706157-byte original SOF programmed with E10 readback. Physical blue4 discovery/lock led briefly to APPROACH, then LOST/SEARCH and NOT_FOUND/SCAN_BUDGET after 22.2096082 seconds of observation. No DOCKED or reverse SEARCH; zero-speed cleanup completed |
| E7070011, historical programmed version | Five-field tuning in stopped VISION_ONLY; LOST requires complete ACQUIRE across relevant HOLD/source interruptions | Runtime control 996/358 per sign, legacy 847/289. First R6 FAIL 302.015209 retained; final fresh R6 PASS 219.199994 seconds / 13 PASS plus CAUGHT. Full Compilation 1375.853 seconds/gate 26.278 seconds, programming and stationary tuning PASS; original/search3 search NOT_FOUND, turn3/turn5 INCOMPLETE; final 3/5/4/3/40 comparison INCOMPLETE; lower speed did not resolve twitching/overshoot and testing concluded |
| E7070012, current release | Independent ALIGN total duration/optional startup stage; stopped-V1 atomic tuning/readback | Protocol/control, first R6 PASS223.404755 seconds, full build/programming and physical stationary tuning PASS. First three trials INCOMPLETE; fourth limited realignment accepted by user; fifth INCOMPLETE 60.0399573 seconds/near-obstacle HOLD without DOCKED. Sixth tolerance30 trial physically confirmed continuous differential approach before diagnostic STOP at first LOST; seventh independent approximately 41 cm task DOCKED, J3292/user ruler approximately 370 mm retained separately; eighth outside-view search found/recovered but remained INCOMPLETE 60.1513566 seconds; ninth turn4 diagnostic improved direction and stopped at first APPROACH; tenth full search INCOMPLETE 60.0024068 seconds; equal 5/5 requests did not establish physical straight travel |

Real hardware corrections and three complete-revolution observations on the current plastic floor have been demonstrated. Six-bay floor closed-loop operation and precise 360° scanning remain unverified. Earlier hardware work mainly used a raised chassis; subsequent ground records are labelled separately. This README distinguishes implementation, version-specific observations and procedures still to perform. A reproduction procedure is not an execution claim.

Following physical observations and the user's new requirement, E5 sets production `TURN_SIGN=-1` and publishes FAR for a completed, bounded over-range ECHO pulse while retaining signal-fault protection. The production negative-sign control configuration passed 269 checks, the original 12-frame pixel-to-UART path passed, and the full sonar pin test passed 46 checks. E5 Full Compilation **passed in 1173.143 seconds**, followed by a **25.799-second passing post-fit gate**. Final R6 **passed in 239.403059 seconds**, and actual programming/readback confirmed E7070005. The zero-speed FAR/vision evidence and outstanding ground tasks are recorded separately; the first R6 failure remains retained.

<a id="environment"></a>

## 环境与硬件前提 / Environment and hardware prerequisites

**中文**

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

**English**

| Item | Environment used / requirement |
|---|---|
| FPGA / project | DE1-SoC, Cyclone V 5CSEMA5F31C6; `quartus/PartBDebug.qpf` |
| Synthesis and programming | Quartus Prime Lite **18.1.0 Build 625**, Quartus STP and the USB-Blaster driver |
| Host scripts | **Python 3.13**; install project dependencies from `requirements.txt` |
| Formal R6 simulation | **Verilator 5.050**, Bash, GNU Make and a compatible C++ compiler; this machine used Git Bash, the MSYS2 MinGW compiler and `--jobs 4` |
| Targeted RTL simulation | ModelSim Altera Starter Edition **10.5b (2016.10)**; a ModelSim pass does not replace formal R6 |
| Vision input | The real OV7670 camera, existing project camera wiring and official marker cards; VGA for live video and diagnostics |
| Motion and protection | UGV02 chassis UART, real IR receiver, J3 RCWL-1601 ranging, 3.3 V interfaces and common ground |

The working directory on this machine is `C:\Quartus_Projects\ECHO72.0\github_publish\MTRX3700_MajorProject`. Adjust commands to the actual clone directory on another machine. Check camera wiring, power, ground, crossed UART connections and valid J3 echoes before use. Verify wheel direction with the chassis raised before floor tests. VISION_ONLY can debug vision without J3 connected; both motion-capable modes require real valid ranging and IR safety conditions. No J4 sensor has been added, and JTAG does not replace real ranging with fabricated values.

`status --watch` and injection each hold a JTAG session. Close one session before opening another; a busy link is not evidence of a board fault. Pin assignments are listed at the end of this document.

<a id="controls"></a>

## 开关、按键与显示 / Switches, buttons and displays

**中文**

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

**English**

| Control | Current function |
|---|---|
| SW0 / SW1 / SW2 / SW3 / SW4 / SW5 | Select blue bay1 / 2 / 3 / 4 / 5 / 6 respectively; exactly one bit must be high |
| SW6 | Candidate information and local RGB/HSV, colour, digit and rejection diagnostics; two automatic pages of eight slots cover all 16 candidates |
| SW7 | A white centre 8×8 sampling box and the identity of a complete recognized card covering that location |
| SW8 | Axis-aligned bounding-box recognition / perspective bypass; the same camera image and safety chain apply, with observations reconfirmed after the configuration changes |
| SW9 | Camera display without overlays and suspended vision processing; immediately revokes motion authorization; leaving raw mode still requires a new START/POWER |
| IR POWER `0x12` | Start a qualified new task when no emergency stop is latched; does not reset an active task's scan budget |
| IR A `0x0F` | Latch emergency stop and immediately revoke motion permission |
| Red1 card with paired blue reference strip | Establish a real colour sampling window and calibrate; the reference strip is not a numbered blue bay |
| Red2 card | After consecutive confirmation, reselect the current valid switch target; without scan calibration, wait for the new target's three-frame lock before starting; VISION_ONLY only reacquires |
| POWER after emergency stop | The first new press only clears the IR latch and leaves the chassis stopped; release and press again to start |
| KEY0 | Global reset: INTEGRATED, DISARMED and zero speed; selection, colour calibration and scan calibration state are reinitialized |
| KEY1 | Cycle HEX distance / upper NEC16 / lower NEC16 pages; retain camera snapshot operation |

The complete six-switch value must remain stable for approximately 20 ms before selection is established. All zero means `NO_SELECTION`; multiple high bits mean `SELECTION_CONFLICT`. Both clear old tracking and prohibit motion. A valid target is tracked even while disarmed. Red2 can establish a new request boundary for the same physical selection. A synchronized switch change during motion stops and cancels the old task; the new selection requires a new start.

From left to right, the six digits show **HEX5 page/selection status, HEX4 mode, then HEX3–0 data**. HEX4 shows `0` INTEGRATED, `1` VISION_ONLY or `2` CHASSIS_INJECT; **it is not the bay number**. HEX5 shows `n` for a stable all-zero selection or `C` for a stable multiple-selection conflict. A valid single selection shows the current distance page `d` or NEC page `H/L`. Only the page character is replaced by `n/C`; the mode and data continue to show the selected page. During the approximately 20 ms debounce interval, the page character alone does not establish that a new selection is stable. HEX3–0 show distance in millimetres or the selected NEC data; invalid distance is blank. E5 displays ` FAr` for confirmed far range. Use `chassis_debug.py status` for complete task state, target number and failure reasons.

Read distance from only the rightmost four digits, HEX3–HEX0, on page `d`: ordinary numeric values are **decimal millimetres**. For example, `d2 0520` means 520 mm (52.0 cm); the left `d2` means “distance page plus CHASSIS_INJECT mode” and is not part of the distance. E5's ` FAr` denotes confirmed over-range/normal no-reflection behaviour, encoded internally as `distance_mm=4000 && distance_valid=true`; it is **not a measured four metres**. The CLI exposes `distanceKind=MEASURED/FAR/INVALID` and `distanceFar`; older E4 `4000,false` records remain INVALID. KEY1 cycles `d → H → L`. On H/L, the right four digits are hexadecimal NEC remote-control data, not range. Invalid distance blanks all four right-hand digits; a blank display does not mean 0 mm.

H shows the upper 16 bits of the last valid complete NEC word. Its rightmost two digits are the command byte: `12` for POWER and `0F` for A, giving examples `H0 ED12` and `H0 F00F`. L shows the lower 16 address bits of the same word. Both data fields remain blank until a valid complete word is received. They show the last received key code, not the current emergency-stop latch or wheel speeds. Release KEY1 before pressing it again to advance one page; holding it does not repeatedly advance. Its snapshot function neither freezes VGA nor changes operating mode.

The display, controller and JTAG status use the same ultrasonic `distance_mm`, with a new sensor measurement approximately every 100 ms. A separately timed JTAG snapshot may differ from the visible display by an update. Millimetres are the code's defined unit; absolute ruler accuracy has not been established. Adjusting the reflector setup changed an observed reading from 379 mm to 520/521 mm, while the actual reflecting surface and ruler origin were not established. This is not a basis for changing the conversion factor or claiming distance calibration.

LEDR0 is nonzero motion permission; 1 is the latched IR emergency stop; 2 is valid distance, including FAr; 3 is docked; 4 is the current ultrasonic stop reason, with IR taking priority; 5 is UART busy; 6/7 pulse for complete/repeat NEC frames; 8 is a confirmed, fresh motion target; 9 is disarmed with valid distance. LED0 is not the ARM flag and LED9 is not an all-system READY indicator: it does not check every vision, selection or IR condition. `LEDR0=0`, completion of a zero-speed JSON message and physical standstill are separate facts. NEC repeat frames and repeated complete POWER frames cannot turn one held press into both release and restart. A new key event requires approximately 180 ms of silence.

<a id="vision"></a>

## 红1校色与视觉诊断 / Red1 calibration and vision diagnostics

**中文**

红1校色要求真实识别到唯一红1及其几何配对的蓝色参考条。连续三个当前配置的健康帧确认后，采集八个独立合格帧，并在后续SOF边界原子提交颜色阈值/配置版本。校色期间不允许运动；红2不能抢占校色。已经成功的校色不会因为红1一直留在画面里而反复执行；初始未校色流程可自动重试，显式重启可用下文的`calibrate --arm`。

默认分割最低值为红48、蓝20。校色由真实采样得到颜色最低值，不是自动调节所有识别参数：白色笔画最低值84、严格锚点白色门限及几何/数字检查仍属于固定算法参数。当前BCTL不提供任意红/蓝阈值写入。校色ACK只证明重新使能请求被接受，须通过`calibrated`、`calibrationSampleFrames=8`、配置版本及终态事件确认完成。

摆位时让卡牌完整入镜，保留背景余量并避免反光、明显模糊及大面积红色碎杂背景。颜色候选每色最多15个活动标签、共享16个完成候选；容量溢出会拒绝整帧。SW6能检查被拒绝候选的颜色、UNKNOWN及原因，SW7能检查中心局部RGB/HSV；局部采样不等于中心位置独立OCR。正常数字仍来自真实像素和每张卡的锚点/笔画，不从场景固定位置或候选索引推断。

**English**

Red1 calibration requires a uniquely recognized real red1 and its geometrically paired blue reference strip. Three consecutive healthy frames from the current configuration confirm the pair. Eight independent qualified frames are sampled, and colour thresholds/configuration are committed atomically at a subsequent SOF. Motion is inhibited during calibration, and red2 cannot preempt it. A successful calibration does not restart simply because red1 remains visible. Initial calibration can retry automatically; an explicit rearm is available through `calibrate --arm` below.

Default segmentation minima are red 48 and blue 20. Calibration derives colour minima from real samples; it does not automatically tune every recognition parameter. The white-stroke minimum of 84, strict white-anchor threshold, geometry gates and digit checks remain fixed algorithm parameters. Current BCTL has no arbitrary red/blue threshold-write command. A calibration ACK only confirms acceptance of the rearm request. Check `calibrated`, `calibrationSampleFrames=8`, configuration version and the terminal event to establish completion.

Keep the complete card inside the frame with a background margin, avoiding glare, substantial blur and fragmented red clutter. Candidate extraction supports up to 15 active labels per colour and 16 shared completed candidates. Capacity overflow rejects the whole frame. SW6 exposes rejected candidates, UNKNOWN and reason codes; SW7 shows local centre RGB/HSV. A local sample is not independent centre OCR. Digits still come from real pixels and each card's anchor/strokes, not from a fixed scene location or candidate index.

### VGA画面怎么读 / Reading the VGA image

**中文**

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

**English**

The normal view has a portrait camera image in the centre with red/blue colour contours. Accepted cards receive white labels on a red background for `R1/R2` or a blue background for `B1–B6`; the paired blue reference is labelled `BJ`. These identify recognized cards and do not establish task arming or the controller's qualified target lock. The current view has no permanent large detection rectangles, green lock box or `MODE/ARM/selected/LOCK` text row.

| Display element | Meaning |
|---|---|
| `CAL:W / B / Y` | Waiting for calibration / calibration busy / calibrated; keep the cards and camera steady while busy |
| `CFG`, `SAMPLE` | Current colour configuration and calibration sample progress, useful for checking that calibration actually completed |
| `FRAME:GOOD / BAD / STALE`, `VGA/META` frame numbers | Frame health, metadata freshness and frame-association diagnostics; GOOD does not mean ARMED |
| `RED2:RESELECT` | A fixed function hint, not an indicator that a red2 event just occurred |
| `STATE` | B's calibration/interaction state, not SEARCH, ALIGN or DOCKED navigation state |
| SW6, `PAGE:1 / 2` | Automatic changes about every two seconds: slots0–7 on page1 and8–F on page2; candidate colour, digit or UNKNOWN, REF, rejection code E and RGB/HSV. Small yellow sampling marks associate with slot numbers |
| SW7, `CENTRE8X8` | The white centre 8×8 box's local colour/RGB/HSV and the identity of a complete recognized card covering it; no-card and ambiguous cases are explicit |
| SW8, `BYPASS:1` | Axis-aligned bounding-box recognition for algorithm comparison. It retains the same camera view, does not display a rectified image, and does not bypass IR/J3 protection |
| SW9 | The camera image without diagnostic overlays, retaining the established portrait orientation; leaving it requires a new start |

The colours have different roles: blue1–6 are selectable docking targets, the blue reference strip supports red1 calibration only, and red2 requests reselection/start. Present red2 beside the target without covering the blue card or J3, and keep the hand/card from becoming a closer reflector. A closer object may cause protective stopping or satisfy the docking distance before the intended board is reached.

<a id="modes"></a>

## 三种模式 / Three operating modes

**中文**

| 模式 | 感知来源 | 是否允许运动 |
|---|---|---|
| INTEGRATED，上电默认 | 真实相机和 B 算法 | 明确启动且真实安全条件满足时允许 |
| VISION_ONLY | 真实相机和 B 算法 | 始终零速；J3未连接也可选牌、追踪和校色 |
| CHASSIS_INJECT | FPGA按25 Hz生成的合成视觉报告 | 同一真实C控制器、IR/J3保护和UART；另外要求有效主机租约 |

切模式不启动任务，撤销旧授权并建立新请求/报告边界。真相机故障和校色状态继续保留；注入模式只隔离这些非活动来源条件，切回真实模式立即重新适用。IR和J3在两种可运动模式中始终有效。

上电、KEY0或切换模式后，红2首先处于禁止重触发状态；先移开红2，使算法连续三个健康帧判定红2缺席，再重新出示并连续确认三个健康帧中唯一有效的红2，才能产生一次新启动请求。这是识别结果的缺席/出现边界：实物仍留在画面但连续漏识三帧，也可能重新满足重触发条件。STOP、急停、选择变化、原始相机模式和适用安全阻挡也撤销旧呈现；恢复后同样需要上述新边界。活动任务中红2不重置选择、任务或扫描预算。非活动任务重锁后最多等待1秒；未完成扫描标定时，必须等到新请求的目标完成三帧锁定才启动，已标定时可由健康无目标帧开始搜索。未标定时应让红2与所选蓝牌同时完整入镜；只展示红2而没有选定蓝牌，会等待超时并保持停车。STOP、IR、开关变化、模式切换、SW9、fatal或超声危险取消待启动操作。距离不安全时不接受红2启动；恢复本身不会保留并重放旧启动请求。

合法START还要求当前来源健康、距离有效且超声HOLD已解除。控制器不会保存一次不安全START，等待条件恢复后偷偷启动。JTAG START的事务ACK表示命令已解析，CLI随后检查控制器是否真的进入ARMED。

红2是START请求，不是“运行固定2秒再停车”的命令。正常任务根据视觉目标、安全条件、扫描预算及停靠状态推进。架空时轮转无法真实改变车体偏角或与目标的距离，不能用此条件要求完成落地DOCKED；目标移出后的停车与主机定时STOP也应分别观察。

**English**

| Mode | Perception source | Motion |
|---|---|---|
| INTEGRATED, power-up default | Real camera and B vision processing | Allowed after an explicit start and real safety qualification |
| VISION_ONLY | Real camera and B vision processing | Always zero speed; selection, tracking and calibration work without J3 connected |
| CHASSIS_INJECT | Synthetic vision reports generated in the FPGA at 25 Hz | The same real C controller, IR/J3 protection and UART; additionally requires a valid host lease |

A mode change never starts a task. It revokes the previous authorization and creates new request/report boundaries. Real-camera faults and colour calibration are retained. Injection only isolates conditions belonging to that inactive source; switching back immediately reapplies them. IR and J3 remain active in both motion-capable modes.

After power-up, KEY0 or a mode change, red2 starts in a state that blocks retriggering. First remove it so the algorithm reports red2 absent in three consecutive healthy frames, then present a uniquely accepted red2 for three consecutive healthy frames. This is a boundary in recognition results: three missed detections can rearm it even if the physical card remains in view. STOP, emergency stop, selection changes, raw camera mode and applicable safety holds revoke the previous presentation; recovery requires that new boundary again. Red2 does not reset selection, task state or scan budget during an active task.

An inactive task waits at most one second after red2 reselects. If scan calibration is absent, the new request must acquire a three-frame target lock before starting. With scan calibration, healthy NOT_FOUND frames can qualify a search. Without scan calibration, keep red2 and the selected blue card fully visible together; showing only red2 without the selected bay times out and leaves the vehicle stopped. STOP, IR, switch changes, mode changes, SW9, fatal faults or ultrasonic hazards cancel a pending start. Unsafe distance rejects a red2 start; recovery alone does not retain and replay that old start request.

A legal START also needs a healthy current source, valid distance and a released ultrasonic HOLD. The controller does not save an unsafe START for later execution. A JTAG START ACK only means that the transaction was parsed; the CLI subsequently checks actual controller arming.

Red2 is a START request, not a command to run for exactly two seconds and stop. A normal task progresses according to the visual target, safety conditions, scan budget and docking state. With the chassis raised, wheel rotation cannot actually change body heading or distance to the target, so this setup cannot establish floor-level DOCKED operation. Stopping after target removal and a timed host STOP must also be observed separately.

<a id="commands"></a>

## 可运行命令 / Executable commands

**中文**

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

**English**

Run commands from the repository root with Python 3.13. The example selects the executable actually used on this machine, avoiding the system Python 3.8 or an unavailable launcher. Change the path on another machine. Tools locate Quartus automatically; if necessary, put `--quartus-bin C:\intelFPGA_lite\18.1\quartus\bin64` before the subcommand. Supply both `--cable` and `--device` when selecting a target explicitly.

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

`status --watch` runs continuously. Press Ctrl+C to end the observation session before continuing with mode/injection commands. Use `--help` for supported subcommands and options. There is no standalone `chassis_debug.py start` subcommand: real integrated operation normally starts through IR POWER or a new red2 presentation; injection uses `--arm`.

With no other JTAG session open, real vision status, calibration and capture are available through:

```powershell
& $pythonExe tools/echo7.py doctor
& $pythonExe tools/echo7.py status
& $pythonExe tools/echo7.py calibrate --arm
& $pythonExe tools/echo7.py capture --fresh
```

`echo7.py status` reads BCTL colour/candidate/report state. `chassis_debug.py status` reads CCTL selection/safety/task state. Capture retains real RGB565, result words and CRC/version checks; use the output location reported by that invocation. In the integrated production top, C exclusively owns SELECT/CLEAR. Older B debugging `select/track/locate` commands are not substitutes for physical switch selection; speech commands are unsupported.

Use `observe` to save a bounded sequence. Physical SW0–SW5 still select the target. The command only reads CCTL then BCTL within one persistent session; it does not select a bay, change mode, ARM, renew a lease or STOP. Ending observation does not cancel a running INTEGRATED task. Set the mode and physical switches before running:

```powershell
& $pythonExe tools/chassis_debug.py observe --samples 30 --out build/observations/bay1-normal1.json --label bay1-normal-trial1
# Alternatively sample for a duration; choose either --seconds or --samples.
& $pythonExe tools/chassis_debug.py observe --seconds 8 --out build/observations/bay1-window.json --label bay1-window
```

`--samples` counts poll pairs, not necessarily new frames. `--interval` pauses after each pair and defaults to 0.1 seconds. JSON retains bad, unlocked and repeated samples, counts distinct C/B frames separately, and includes physical selection, mode, versions, thresholds, request tags and each read's start/end time. CCTL and BCTL freeze independently: **a pair is not a same-frame snapshot**. `COMPLETE` means collection completed, not recognition or motion acceptance. Ctrl+C or a transport error preserves records already read, including a partial CCTL sample if BCTL fails. Output must be a new file; existing evidence is never overwritten.

Static SW8 vision comparisons can start in VISION_ONLY. Keep the same blue card, physical selection, camera position/focus, card placement and illumination, with SW9 off. Collect three normal runs with SW8=0 and three bypass runs with SW8=1, using the same `--samples` count each time. Give each run a new filename and label, such as `normal1.json` through `normal3.json` and `bypass1.json` through `bypass3.json`. After changing SW8, let the current request/configuration stabilize; do not change selection, calibrate or switch mode during a run. Then compare offline:

```powershell
& $pythonExe tools/compare_observations.py --normal build/observations/normal1.json build/observations/normal2.json build/observations/normal3.json --bypass build/observations/bypass1.json build/observations/bypass2.json build/observations/bypass3.json --out build/observations/comparison.json
```

Without `--conditions-confirmed`, the result is `UNCONFIRMED_CONDITIONS`, exit 2. Only after the operator actually checks unchanged camera/card/lighting conditions for these six runs, add `--conditions-confirmed 'describe the actual confirmation'`. The comparator checks build, algorithm/colour profile, physical target, operating mode and poll count across all six runs, plus stable request/configuration and the expected SW8 value within each run. Raw SW9 display, reused runs and invalid time order are rejected. `COMPARISON_VALID` only means the inputs match; bad frames, lost locks and stale data remain visible for each mode. Both all-poll and distinct-frame summaries are reported. FPGA capture-to-completion time is not image-change-to-UART or mechanical response latency. Three static pairs for one selected bay do not establish six-bay floor-level acceptance.

The old `echo7.py test --hardware [--trials N]` and `autodebug` depend on automatic BCTL SELECT/CLEAR, which conflicts with the production top's sole request owner. They now return `BLOCKED`, exit 2, and point to `observe`. `autodebug` stops before building, programming or accessing the board. Historical B trial parsing/scoring remains available for old evidence; the old commands cannot certify that all six bays were automatically tested on the current top.

U is the rotated image coordinate `0..239`; V is `0..319`. U80/U120/U160 mean left/centre/right. `--hold` is in seconds and defaults to 3. Without `--arm`, a session updates templates but does not start a task. Mode changes, heartbeats and read-only status commands do not start tasks either.

Continuous injection updates the template, renews the lease and starts within one persistent Quartus STP session. Normal exit or Ctrl+C attempts STOP. An abnormal host exit causes the FPGA lease to expire after approximately 500 ms, directly revoking injection permission. Renewing the lease does not restart motion. Stopping frames while retaining heartbeats is still caught by the approximately 150 ms report freshness guard. INTEGRATED does not depend on JTAG heartbeats.

`scenario no-target-search --arm` reads the FPGA's current `scanBudgetUs` and holds the synthetic no-target template for the budget in seconds plus 3 seconds. E5 uses the final zero-speed message, 200 ms settling, 900 ms confirmation and polling margin; the default 10-second budget gives a 13-second session. E7 and E8 use a 1.5-second dwell, so host session duration alone cannot establish task completion. The same session continuously prints CCTL state and renews the lease between pages, exposing SEARCH, final ACQUIRE, NOT_FOUND or real HOLD. HOLD does not add search rotation time, so inspect the retained states rather than assuming the budget completed; exit still attempts STOP. This command does not set scan calibration or equate raised-wheel rotation with a ground revolution.

**Stop active injection using Ctrl+C in its owning process.** Use a separate `stop` command only when the JTAG link is idle. The tool rejects contention with another chassis session; inability to open the link does not mean STOP was delivered. Do not run another BCTL/GRAB process alongside an active injection session.

Play a sequence with `play <JSON-file> --arm`. The file is a nonempty JSON array of objects, for example:

```json
[
  {"x": 80, "visible": true, "hold": 3},
  {"x": 120, "visible": true, "hold": 3},
  {"x": 160, "visible": true, "hold": 3},
  {"visible": false, "hold": 4}
]
```

Each row can also specify `y`, `quality` or `frames_enabled`. Users do not maintain internal tags, frame IDs or capture timestamps. Templates are staged and committed atomically; incomplete transactions cannot become partially updated observations. CCTL uses stable 64-bit transactions, toggle/ACK and error codes. STATUS freezes a 16-word snapshot containing mode, switches, task state, request/frame/configuration, age, search budget, logical speeds, real J3, IR and UART zero-completion state.

Observe `mode`, `inputSource`, `selection`, `digit`, `requestTag`, `frameId`, `sourceHealthyFresh`, `targetObserved`, `targetLockedFresh`, `taskArmed`, `motionPermit`, `distanceValid`, `sonarHold`, `irEstop`, `failure` and `zeroSent` together. Command acknowledgement, a new frame, target lock, task authorization and physical movement are distinct facts. One field alone cannot establish that the complete chain passed.

<a id="tuning"></a>

## E11：停车状态下的小范围调参 / E11: bounded parameter tuning while stopped

**中文**

本节记录E11首次引入的通用接口。E14新增policy可调正常停车/减速距离及驻留，生产启动值也已变化，以上方E14表为准。

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

**English**

This section records the original E11 generic interface. E14 adds policy tuning for normal stop/slow distances and dwell, with different production boot values; the E14 table above takes precedence.

These five-field tuning controls were introduced in E11 and remain supported in E12. Older E10 firmware does not support tuning; the updated tool rejects writes to it instead of treating an old status word as a tuning register. With no options, `tune` only reads status, including `tuningSupported` and `tuning`. Specified fields are merged with all five current values, written atomically as one configuration and read back for verification. Values must be integers within the table, and `approach > fine`. Speeds are logical cm/s controller requests, not motor PWM, measured wheel speeds or direct wheel teleoperation.

**Reset defaults differ from the current experiment:** defaults are 4/4/5/3/30; the historical E11 session ended with 3/5/4/3/40 and 15.1 seconds. Settings are not written into the SOF; turn5 ended INCOMPLETE, and approach4 also ended INCOMPLETE; these are experimental settings, not a validated recommendation.

| CLI field | Range / default | Effect |
|---|---|---|
| `--search` | 3–5 cm/s / 4 | Equal-magnitude normal SEARCH and bounded reverse-SEARCH turning; changing it invalidates scan-time calibration |
| `--turn` | 3–5 cm/s / 4 | Large-error ALIGN pivot speed; fine pivots for error≤30 but outside the centred band remain fixed at 3 cm/s |
| `--approach` | 4–8 cm/s / 5 | Centred forward speed and faster differential wheel beyond 500 mm; must exceed fine |
| `--fine` | 3–4 cm/s / 3 | Centred forward speed at 350–500 mm and slower differential wheel; near-range faster wheel is fine+1 |
| `--tolerance` | 10–40 pixels / 30 | Accepted band on each side of U120, default U90–150; also used for centred docking qualification |

Writes require **VISION_ONLY, disarmed, no motion permit, both wheel commands zero and zeroSent=true**. The CLI does not automatically STOP, switch modes, ARM, renew a lease or start a task; the FPGA independently enforces the stationary boundary. Explicitly stop and select VISION_ONLY first, then verify physical standstill and status. These example read/write commands do not start a task:

```powershell
& $pythonExe tools/chassis_debug.py tune
& $pythonExe tools/chassis_debug.py mode vision
& $pythonExe tools/chassis_debug.py status
& $pythonExe tools/chassis_debug.py tune --turn 4 --tolerance 30
& $pythonExe tools/chassis_debug.py tune --defaults
```

`--defaults` restores all five values to `search/turn/approach/fine/tolerance = 4/4/5/3/30` and cannot be combined with individual fields. All five readback values must match the requested configuration; a mismatch leaves delivery/retention unconfirmed. Parameters last only for the current FPGA session: KEY0, power loss or reprogramming restores defaults, without persistent storage.

**Any change in search speed clears scanCalibrated, including restoring defaults when that changes search.** A new speed cannot reuse or mathematically scale the old 13.6-second value. Revalidate actual ground scanning time at the new setting and scene before using `scan --seconds ... --calibrated`. Returning to a previously measured speed still requires checking the applicable scene/configuration and explicitly restoring that record; defaults alone do not restore calibration. Changes to the other four fields retain scan calibration; physical changes to floor, supply or tyres still require checking whether previous measurements apply. Tuning does not expose the 250/300/350/500 mm distance boundaries, IR emergency stop, visual freshness/three-frame lock, 1.5-second dwell or 120-second task deadline.

Transport uses CCTL opcode11 with one 32-bit configuration word. STATUS word13 declares support with high byte `0xA1` and returns the five fields in its low 22 bits. The E11 top passes its actual design ID; Tcl accepts the E707 design family while strictly checking CCTL magic, protocol metadata and the 16-word count. Without the A1 capability, old firmware reports `tuningSupported=false` and writes are rejected before transmission. Design-family compatibility neither bypasses the protocol nor adds tuning to old firmware. E11 requires the matching updated `tools/tcl/chassis_session.tcl`; the old host hard-coded E7070001 and rejects the new board identity. The new host can read old E707 boards but cannot write tuning without the capability tag.

<a id="pulse"></a>

## E12：独立设置ALIGN总时长与起步段 / E12: independent ALIGN duration and startup stage

**中文**

本节保留E12通用范围/默认值；E14生产启动为200/200/60/6，命令`--defaults`仍是旧通用值，详见上方说明。

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

**English**

This section retains E12 generic ranges/defaults. E14 boots with200/200/60/6, while the CLI `--defaults` remains the older generic values described above.

E11 ground trials showed twitching, unequal wheel startup and overshoot during short turns; lowering the forward request did not resolve them. E12 adds a separate `pulse` configuration for controlled physical comparisons. It affects only in-place **ALIGN**, without adding a kick to SEARCH (including reverse recovery) or APPROACH, and never starts a task. Accepted parameter ranges are interface limits, not mechanically validated operating ranges.

| CLI / status field | Range and step / default | Meaning |
|---|---|---|
| `--min-ms` / `minMs` | 20–300 ms, step 10 ms / 20 | Lower bound for one ALIGN total requested duration |
| `--max-ms` / `maxMs` | 20–300 ms, step 10 ms / 100 | Upper bound for one ALIGN total duration; must be ≥minMs |
| `--kick-ms` / `kickMs` | 0–100 ms, step 10 ms / 0 | Initial-stage duration; zero disables it and the total duration truncates it |
| `--kick-speed` / `kickSpeed` | 3–8 cm/s, integer / 5 | UGV02 UART speed-request magnitude during the initial stage, not measured speed, PWM, current or torque |

When ALIGN is needed, the existing error rule selects `2 ms × abs(U−120)` and clamps it between minMs/maxMs; a target already inside the centred band does not create a pivot. **Total duration includes the kick rather than adding it afterward.** ALIGN entry latches the total duration and both speeds: kickSpeed is used for `min(kickMs, selected total duration)`, then the original direction continues at `tune --turn` (3–5 cm/s). A small error outside a narrower centred band retains the fixed 3 cm/s second stage. For example, a 40 ms total with kickMs60 permits at most a 40 ms initial stage and no later slow segment; this is a logical example. Kick speed is not required to exceed the second stage. Default kickMs0 disables it, and the 20/100/0/5 defaults preserve E11 short-turn behaviour.

With no options, `pulse` only reads `alignTimingSupported` and `alignTiming`. Specified fields merge with the current four values, are committed in one atomic write and are independently read back for an exact match. `--defaults` restores 20/100/0/5 and cannot be combined with field options. Writing requires **VISION_ONLY, disarmed, no motionPermit, both logical wheel commands zero and zeroSent=true**. The CLI does not switch mode, send START/ARM or renew a lease; the FPGA independently rejects unsafe-state or invalid-range writes.

```powershell
# Read capability and all four values without renewing a lease or starting
& $pythonExe tools/chassis_debug.py pulse
# Write only after confirming stopped VISION_ONLY; these values equal defaults
& $pythonExe tools/chassis_debug.py pulse --min-ms 20 --max-ms 100 --kick-ms 0 --kick-speed 5
& $pythonExe tools/chassis_debug.py pulse --defaults
```

minMs is the lower bound of the **calculated nominal total duration**, not a mandatory minimum motion time. Entry into the centred band, crossing direction, target loss, IR or J3 protection can stop the request earlier, below minMs. Kick speed is a UGV02 UART speed request; overcoming static friction, simultaneous wheel startup and actual speed require physical observation.

This configuration is independent of E11's five-field `tune`: `pulse --defaults` leaves search/turn/approach/fine/tolerance unchanged, and `tune --defaults` does not restore pulse settings. Pulse-only changes retain scan calibration; the host verifies scanCalibrated, scanBudgetUs and all five tuning values are unchanged. Changing search still clears calibration. Both groups are volatile: KEY0, power loss or programming restores their respective defaults, and scan calibration must be checked again. Pulse tuning does not expose the 250/300/350/500 mm boundaries, IR protection, visual freshness, stopped dwell or overall task deadline. Pulse expiry, entry into the centred band, crossing the error direction or safety interruption still invoke the existing stop/reconfirmation rules without promising mechanical settling time.

The protocol uses independent **CCTL opcode12**, with only the low 18 bits of one 32-bit write valid, time encoded in 10 ms units and higher bits required to be zero. STATUS **word15 bits27:20 contain 0xA2**, bits19:2 return the four fields, bits1:0 retain the mode and the high four lease/template/scan/frames flags remain unchanged. Opcode11 and word13's A1 five-field tuning interface are unchanged. An older E11 board without A2 reports `alignTimingSupported=false`; pulse writes are rejected before transmission while ordinary reads and its existing tuning capability remain usable. Use the matching E12 host/Tcl instead of interpreting an old status word as a pulse configuration.

Focused interface and main control simulation, plus host tests, have passed at this point. Stationary board writes and independent readback have now passed; physical speed stages, simultaneous wheel startup, reduced overshoot and search-to-dock still require their own evidence; neither readback nor logical timers establishes those outcomes.

<a id="navigation"></a>

## 搜索、对准、停车与恢复 / Search, alignment, docking and recovery

**中文**

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

**English**

The main path is `IDLE → SEARCH → ACQUIRE → ALIGN → APPROACH → DOCKED`, with `LOST`, `HOLD` and `NOT_FOUND` states. Disarmed operation only tracks. With E5's production `TURN_SIGN=-1`, SEARCH rotates with logical left/right speeds of `+4/-4 cm/s` only while frames are fresh and healthy, real safety conditions pass, and budget remains. Healthy NOT_FOUND reports can sustain search; a target lock is not required for search activity. E4 used −4/+4, and its historical records are retained.

One unambiguous target observation with correct identity, time and configuration stops search. E5 ACQUIRE first waits for a complete zero-speed UART message, then dwells for 200 ms before establishing a new capture fence. Alignment/approach require three independent new frames after that fence plus a locked result. The confirmation window defaults to 900 ms. The physical short-turn probe showed continued image movement beyond 200 ms: zeroSent or expiry of the dwell does not establish mechanical standstill. E6's board default is now a 1.5-second dwell, with focused logic simulations passed but physical settling still unverified.

E5 ALIGN continuously corrects with opposite wheel speeds of 4 cm/s; U110–130 is centred. APPROACH uses 5 cm/s beyond 500 mm and 3 cm/s between 350 and 500 mm. A reliable aligned target reaching 350 mm produces DOCKED. Target loss immediately stops translation, first attempts stationary reacquisition, then searches within the remaining budget. DOCKED and NOT_FOUND revoke task authorization: a new image or recovered distance cannot restart them. A new task can be explicitly started without a global reset.

The ALIGN behaviour introduced in E6 and programmed in E7 latches direction, speed and pulse duration once on entry. Duration is `abs(U−120) × 2000 µs`, clamped to 20–100 ms; wheel speed is 4 cm/s for error greater than 30 pixels, or 3 cm/s for error at most 30 outside the centred deadband. Expiry, entering the centred region or crossing direction first stops motion and reuses ACQUIRE: the default 1.5-second dwell is followed by a fresh fence and three new frames before another turn/approach decision. SEARCH remains at 4 cm/s, with the same IR/J3 protection and FAR semantics. Logic simulations passed, but E7's physical trials still showed one-sided short movements and crossing the centre. Neither 1.5 seconds as a measured settling bound nor the pulses as an overshoot cure is established; reliable simultaneous wheel startup at 3 cm/s remains unproven.

E7 changes only the default pulse arithmetic in `motion_fsm`: an 8-bit absolute error is clamped to 10–50 in 6 bits, then 17-bit shifts/subtractions produce the original pulse duration. All 256 default U inputs match numerically, while non-default configurations retain the complete generic fallback. Speed tiers, duration limits, SEARCH, dwell, capture fences and protection parameters remain unchanged. Focused control regression, E7 formal R6 and full post-fit timing passed, and the firmware was programmed. That timing correction did not eliminate the motion problems observed in subsequent real tasks.

E8 adds continuous forward steering only **after the controller is already in APPROACH**, while the target remains healthy/locked and range exceeds 350 mm. U110–130 remains centred, retaining 5/5 cm/s beyond 500 mm or 3/3 between 350 and 500 mm. At U75–109 or U131–165, both wheels are commanded forward: 5/3 cm/s farther away or 4/3 closer, selecting the faster wheel request according to target direction. With the production negative turn sign, low U requests a faster logical left wheel and high U a faster logical right wheel. Leaving U75–165, or reaching ≤350 mm while off-centre, immediately cancels forward motion and enters ACQUIRE. After a complete zero-speed UART message, a 1.5-second dwell and three confirmed new frames beyond a fresh fence precede any ALIGN decision, preventing immediate wheel reversal after forward travel. DOCKED still requires the existing safe conditions, centring and range ≤350 mm. START, SEARCH, the original ALIGN pulses and IR/J3/FAR protection remain unchanged. The function passed focused control, formal R6 and Full Compilation/post-fit, and is now programmed. Real closed-loop results still require separate confirmation.

E9 grants recovery permission only when a target observed during **normal forward SEARCH** triggers ACQUIRE. A reverse step at 4 cm/s for 150 ms is allowed only after confirmation times out and the target has left. There are at most three steps per task, reusing SEARCH with reversed direction. Permitted reverse-command time also consumes `scanElapsedUs`, retaining the same total budget and `taskStart` without restarting time. Each step completes a zero-speed UART message, waits 1.5 seconds, creates a fresh capture fence and requires three new target-confirmation frames. Successful lock, source failure, HOLD or cancellation clears permission; HOLD does not replenish used steps. Empty-scene search without a prior sighting does not trigger reverse recovery. Other ALIGN/APPROACH, safety and FAR behaviour follows E8. Implementation and tests are frozen and focused control regression passed. Formal R6, Full Compilation/post-fit and programming/identity verification passed; the physical search-to-dock trial is INCOMPLETE after discovery/lock and repeated alignment, with no DOCKED within its 60-second observation window. Host STOP ended the run; reverse SEARCH did not occur, so physical reverse recovery remains unverified.

The historical search4 budget of 13.6 seconds came from three physical observations of **continuous forward scanning**. E9 reverse recovery consumes the same total budget, reducing net forward swept angle. It remains bounded motion time, not precise 360° calibration; the original revolutions do not guarantee a full revolution with reverse recovery enabled. E9 restored that 13.6-second record at the time. The later E11 experiment used search3 and 15.1 seconds, based on two single-circle observations plus one double-circle reference; E12 preparation restores the same-speed, same-floor basis; 13.6 seconds is not the current experimental budget.

E5 alignment commands logical `+4/-4` for U<110 and `-4/+4` for U>130. B's fixed coordinates are `U=floor((native yMin+yMax)/2)` and `V=floor((638-native xMin-native xMax)/2)`. After the VGA 90-degree rotation, screen left/right corresponds to U, not V; `orientationProfile` affects glyph/anchor reading only. A static physical check placed blue1 at approximately U80 in front of the robot's left side and U174 on its right, with V near 158. E4's −4/+4 command physically turned clockwise from above, motivating E5's sign correction. In E5's first ground revolution, the user confirmed that logical +4/−4 physically turned anticlockwise, verifying the direction correction. The physical P1/P2 wiring cause remains unisolated, and alignment toward a real target needs separate closed-loop evidence; B coordinates were not changed.

Scanning currently uses **accumulated authorized search-turn command time**, not verified heading feedback. Only permitted SEARCH rotation consumes this budget; ACQUIRE/HOLD waits do not. A separate 120-second task wall-clock limit applies. The direction-query receive path is retained, but real feedback has not been validated for angle-based closed-loop scanning.

The default 10-second value is an uncalibrated bounded chassis-debug budget, reported as `SCAN_UNCALIBRATED`. INTEGRATED prohibits formal no-target scanning without calibration, while a reliably visible target can still be aligned with and approached. For an approximately 360° calibrated scan, first make three actual floor trials at the same fixed wheel speed in a clear area, measure a full revolution using direction marks, and record repeatability before setting the measured duration:

```powershell
# Only for this search3/plastic-floor setting: two single circles plus one double-circle reference support 15.1 s, not three precise single circles.
& $pythonExe tools/chassis_debug.py scan --seconds 15.1 --calibrated
```

Changing `scan` stops the task; `--calibrated` confirms an applicable physical measurement. This example is only for the current search3/same-plastic-floor 15.1-second budget (`scanBudgetUs=15100000`), based on two single-circle observations of 14.093147/14.691960 seconds and one 30.014554-second double-circle reference. It is not three precise single circles or exact 360°. The older search4/13.6-second record retains its historical scope. Both budget and tuning are volatile; KEY0/reconfiguration loses them. Recheck speed, floor, supply and measurement records before restoring rather than copying blindly. Reverse steps consume the same budget; the laboratory epoxy floor remains untested, and final confirmation without a target ends NOT_FOUND.

The user subsequently required normal open-space/no-reflection behaviour to mean a distant obstacle. E5 distinguishes three J3 results: 20–3999 mm is measured range; after an actual TRIG, a pulse reaching the driver's approximately 23.3 ms range cap and physically returning low before the transaction's 80 ms deadline produces the `4000,true` FAR sentinel. No rising edge, a pre-existing high level that prevents triggering, a line still high at the deadline, an illegal pulse corresponding to less than 20 mm or stale receiver data remains INVALID. A timeout alone never fabricates FAR; 39 ms is not the only accepted pulse length. The full pin test covers completed 24/39/75 ms pulses.

Actual INVALID/stale data or a valid measured range ≤250 mm immediately prohibits motion and enters HOLD; IR protection remains. Recovery still requires three **new**, valid readings ≥300, including independently confirmed FAR samples. Re-reading one sample does not count; recovery does not clear IR/fatal latches or replenish search budget. Normal 350 mm docking and 250 mm protective stopping are reported separately. The trigger period remains approximately 100 ms and receiver stale limit remains 1 second. E5 extends E4's 30 ms transaction deadline to 80 ms to await a normal long pulse ending, leaving approximately 20 ms before the next trigger. Pulses exceeding this bound remain abnormal; an arbitrarily long high signal is not assumed to mean open space.

Camera abandon, a bad frame for the current request or candidate overflow revokes qualification and establishes a new boundary. Three adjacent fresh healthy frames from the current configuration restore search qualification; these may be NOT_FOUND. Alignment/approach still require renewed three-frame target confirmation. Historical candidate-overflow diagnostics remain visible, but recovering the image no longer requires global reset from E7070003 onward. FIFO fatal and double-bank exhaustion remain inhibiting faults across mode changes or good frames. If the current image keeps overflowing, put the full marker in view and simplify the background; reset cannot repair an invalid image.

UART is 115200, 8N1, with complete `T:1` JSON and a normal 200 ms command heartbeat. A stop takes priority after the complete JSON currently in transmission. Both default wheel polarity constants are −1, so logical forward 5 cm/s sends `{"T":1,"L":-0.05,"R":-0.05}`. Verify actual rotation and forward direction with the chassis raised, then measure stopping error on the floor.

<a id="procedure"></a>

## 三阶段操作 / Three-stage reproduction procedure

**中文**

用户已确认蓝1–6和红色功能牌均为独立打印，可分别移动；这为逐车位摆位提供了条件，尚未完成六个实际地面任务，不能把打印准备记为闭环通过。

1. **VISION_ONLY**：实体SW0–5逐个选择六车位，SW6/7观察局部采样和拒绝原因；确认连续frameId、目标observed/locked、遮挡后丢失与重获。红1校色提交后重新确认；默认阈值也可调图和追踪，无须先完成校色。SW6每120个VGA帧自动换页（60 Hz时约2秒），第一页#0–7、第二页#8–F，页码与采样记录一起保持；编号是候选索引，旁边另列真实识别数字或UNKNOWN。中心RGB/HSV是局部采样，不是独立OCR，SW7仍在两页中连续可用。该阶段不用先使J3有效，轮端始终零速。
2. **CHASSIS_INJECT**：先使实际J3读数有效（E5允许确认FAR），架空检查U=80/120/160对应的轮向与前进极性。用真实反射板检查500/350/250 mm条件；验证无目标搜索、短暂目标出现、丢失、Ctrl+C/租约、IR A及两次新POWER。地面一圈标定只在可容纳整车旋转、四周清空且J3正常工作的场地完成；单个前向J3不证明车身四周空旷。该阶段记录为合成视觉输入。
3. **INTEGRATED**：停止注入进程，模式切回integrated；实体开关选择，IR POWER或呈现红2启动。覆盖真实搜索→发现→驻留确认→对准→接近→停靠，六车位、丢失、障碍、无回波和急停分别记录。可断开电脑，正常任务不依赖主机续租。同场景下SW8正常/旁路各三次，记录真实任务时间、停车误差和画面变化到UART响应延迟。

目前速度下从1 m到350 mm仅理想行驶就约15秒，扫描和确认会增加时间。最终指标以本次实测冻结，不沿用旧proposal的12/18秒目标。

**English**

The user confirmed that blue1–6 and the red function cards are independently printed and can be moved separately. This prepares individual bay placement; it does not establish completion of six physical ground tasks.

1. **VISION_ONLY:** select each of the six bays through SW0–SW5, and use SW6/7 to inspect local samples and rejection reasons. Check advancing frame IDs, observed/locked state, loss under occlusion and reacquisition. Reconfirm after a red1 calibration commit; default thresholds also permit image setup and tracking before calibration. SW6 changes page every 120 VGA frames, approximately 2 seconds at 60 Hz: #0–7 followed by #8–F. The page travels with the captured sample records. These labels are candidate indices; the recognized digit or UNKNOWN is shown separately. Centre RGB/HSV is local sampling, not independent OCR, and SW7 remains available on both pages. J3 need not be valid in this stage; commanded wheel speed remains zero.
2. **CHASSIS_INJECT:** obtain valid real J3 readings (E5 permits confirmed FAR) and raise the chassis to verify wheel direction and forward polarity for U80/U120/U160. Use a real reflector to test 500/350/250 mm behaviour. Check no-target search, brief target appearance, loss, Ctrl+C/lease expiry, IR A and two distinct POWER presses. Ground revolution calibration requires room for the entire vehicle to rotate, clear surroundings and a functioning J3; one forward J3 sensor does not establish clearance around the body. Record this stage as synthetic visual input.
3. **INTEGRATED:** stop the injection process, switch to integrated, select through physical switches, then use IR POWER or a new red2 presentation. Record real search→discovery→settling confirmation→alignment→approach→docking, with separate coverage of all six bays, loss, obstacles, missing echoes and emergency stop. The computer may be disconnected; normal tasks do not require host renewal. Compare SW8 normal/bypass in three trials each of the same scene, measuring task time, stopping error and image-change-to-UART latency.

At the current speeds, travelling from 1 m to 350 mm alone takes approximately 15 seconds ideally; scanning and confirmation add time. Final performance is based on measured results, not the old proposal's 12/18-second targets.

<a id="build"></a>

## 构建与验证 / Build and verification

**中文**

本次E12成功构建位于`build/member_b/20261104T192605_706632Z_build/`，原始SOF为该目录`source/quartus/output_files/PartBDebug.sof`，**6706156字节**，已实际下载并核对E7070012。当前发布副本为`firmware/E7070012/PartBDebug.sof`，与本次成功原产物逐字节一致；仅保留这一份最新release副本，旧E11产物仍可从原build与Git历史追溯。

E6首次Full Compilation目录`build/member_b/20261104T144730_277631Z_build/`的最终`result.json`为 **FAIL**。Quartus编译工具退出0、耗时1183.703秒且fit成功，但两条critical timing warnings在构建警告检查时导致拒收，**未执行独立`timing_gate`步骤，也未生成`timing.json`**；工具退出0不等于本工程时序验收通过。实际STA路径随后定位并用于E7修正，E7独立构建现已通过。E6失败仍保留，E6从未下载，不把新结果回写成旧版通过。

本次发布buildId为 **E7070012**，BCTL/CCTL均由生产顶层传入实际设计ID，须使用配套新版主机/Tcl。控制、R6、完整构建/post-fit、下载与停车pulse均有本版独立证据；原始SOF为`build/member_b/20261104T192605_706632Z_build/source/quartus/output_files/PartBDebug.sof`、6706156字节。`echo7.py program`核对源码和本机成功构建记录；已记录十轮实机：第七轮独立近距DOCKED，第八及第十轮画外任务仍未完成，不能拼接分段为主线通过。

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

文档生成器`tools/render_integrated_datasheet.py`现在生成两种文件：[集成说明PDF](docs/ECHO7_Integrated_Datasheet.pdf)共两页，第一页是功能、组件、模式、红蓝牌、拨码/按键、VGA与数码管的产品操作指南，第二页是正式R5指标表；[独立R5数据表](docs/ECHO7_R5_Datasheet.pdf)严格一页，供课程提交绑定。版本从RTL header读取。R5阈值/目标及来源见[指标说明](docs/R5_TARGETS.md)和`tools/data/echo7_r5_targets.json`；E14当前尚无三次实测，measured/acceptance/claimed grade保持PENDING，不拼接E4/E12历史成绩。四项为标牌类型/编号准确率、capture到result时间、校色收敛时间及350 mm可见目标停靠绝对距离误差；阈值/目标是已说明来源的项目选择，不虚构课程指定等级。详细验证仍保留在`docs/integrated_datasheet_metrics.json`与修复记录中，产品页不塞入测试计数。生成依赖属于独立文档工具，不需要改动主视觉环境的`requirements.txt`：

```powershell
& $pythonExe -m pip install reportlab pypdf
& $pythonExe tools/render_integrated_datasheet.py
```

本机已有当前成功构建记录时，可导出整项目交接ZIP：

```powershell
& $pythonExe tools/export_submission.py --out build/echo7_submission.zip --datasheet docs/ECHO7_R5_Datasheet.pdf
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
| E7070012 | `build/member_b/20261104T192605_706632Z_build/source/quartus/output_files/PartBDebug.sof`；当前发布`firmware/E7070012/PartBDebug.sof`，6706156字节 | Full Compilation/post-fit/实际下载及静止pulse PASS；十轮实物结果保留：第七轮独立近距DOCKED，第八/十轮画外搜索仍INCOMPLETE；volatile实验设置不固化进默认SOF |

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

**English**

This E12 release was successfully built in `build/member_b/20261104T192605_706632Z_build/`. The original `source/quartus/output_files/PartBDebug.sof` is **6706156 bytes**, actually programmed with E7070012 readback. The current release copy, `firmware/E7070012/PartBDebug.sof`, byte-matches that original. Only this latest release copy is retained; prior E11 artifacts remain traceable through the original build and Git history.

E6's first Full Compilation has a final **FAIL** in `build/member_b/20261104T144730_277631Z_build/result.json`. The Quartus compile tool exited 0 after 1183.703 seconds and fitting succeeded, but two critical timing warnings caused rejection during the build warning check. **The separate `timing_gate` step did not run, and no `timing.json` was generated.** Tool exit 0 does not establish project timing acceptance. The actual STA path was subsequently identified and used for E7, whose separate build has now passed. E6's failure is retained; it was never programmed, and the new result does not rewrite the earlier revision as passing.

This release buildId is **E7070012**. BCTL/CCTL receive the actual production design ID; use the matching new host/Tcl. Independent E12 evidence covers control, R6, complete build/post-fit, programming and stationary pulse tuning. The original SOF is `build/member_b/20261104T192605_706632Z_build/source/quartus/output_files/PartBDebug.sof`, 6706156 bytes. `echo7.py program` verifies source and local successful-build provenance; ten physical observations include independent near-target DOCKED in trial seven, while trials eight and ten did not complete out-of-view search-to-dock.

Check the Python path and Quartus tools first. If Python dependencies are missing, run `& $pythonExe -m pip install -r requirements.txt`. Dependency installation is outside R6 timing.

```powershell
& $pythonExe tools/echo7.py build
& $pythonExe tools/echo7.py program
& $pythonExe tools/echo7.py test --rtl --only tb_control_repair tb_chassis_debug tb_pixel_uart_repair
```

Alternatively, open the QPF in Quartus and run Full Compilation; `quartus/output_files/PartBDebug.sof` is the direct-project default. `echo7.py build` uses an isolated directory for each build. The `program` command above uses the SOF recorded by the latest successful local build; `--sof` can explicitly supply that record's absolute path. Programming checks the build source and artifact; an older SOF cannot stand in for a new feature.

Published files use fixed paths: [E7070012 FPGA program](firmware/E7070012/PartBDebug.sof) and [integrated datasheet PDF](docs/ECHO7_Integrated_Datasheet.pdf). The E12 SOF is **6706156 bytes**, copied from the successfully compiled and programmed E12 artifact. To use it directly, select the actual USB-Blaster and FPGA at chain position 2 in Quartus Programmer, add the SOF and execute Program/Configure. BCTL should subsequently read `buildId=0xE7070012`. Position 2 was observed on this DE1-SoC; inspect the chain when changing boards.

A precompiled SOF does not carry a local `echo7.py` successful-build record, so use Quartus Programmer for that path. `echo7.py program` continues to require the artifact matching its local successful-build record; provenance protection is not relaxed. SOF configuration is volatile and must be restored after power loss. Permanent boot-image deployment is not claimed here.

After power loss, reprogram and verify the selected firmware's BCTL version, then use `mode vision` to maintain zero speed and read the current configuration, thresholds and calibration state. Do not reuse the previous session's cfg/tag or colour-calibration conclusion. In the completed E7070004 reprogramming record, all six position-check pairs showed healthy, locked blue1 after adjusting the scene, using the power-up defaults red48/blue20 and configuration0, without colour or scan calibration. KEY0/reconfiguration also clears scan calibration: restore measured seconds with `--calibrated` only when applicable records of three ground trials already exist. See the [repair record](docs/REPAIR_RESULT.md) for programming and recovery evidence. That historical check did not rerun or replace the existing R6 or Full Compilation results. E5 programming is documented separately for that version.

`tools/render_integrated_datasheet.py` now generates two artifacts. The [integrated PDF](docs/ECHO7_Integrated_Datasheet.pdf) has two pages: a product guide covering capabilities, components, modes, red/blue markers, switches/buttons, VGA and seven-segment displays, followed by the formal R5 metrics page. The [standalone R5 datasheet](docs/ECHO7_R5_Datasheet.pdf) is strictly one page for course-submission binding. Version comes from the RTL header. Thresholds/goals and provenance are in the [metric notes](docs/R5_TARGETS.md) and `tools/data/echo7_r5_targets.json`. E14 currently has no three-trial measured set, so measured/acceptance/claimed grade remain PENDING; historical E4/E12 results are not combined into grades. The four metrics cover typed-marker accuracy, capture-to-result time, calibration convergence and absolute stopping-gap error for a visible target at350 mm. Thresholds/goals are documented project choices, not invented course-mandated grades. Detailed build/hardware evidence remains in `docs/integrated_datasheet_metrics.json` and the repair record; test counts do not fill the product page. These are separate document-tool dependencies; the main vision environment's `requirements.txt` does not need to change:

```powershell
& $pythonExe -m pip install reportlab pypdf
& $pythonExe tools/render_integrated_datasheet.py
```

With a current successful local build record, export the integrated hand-off ZIP:

```powershell
& $pythonExe tools/export_submission.py --out build/echo7_submission.zip --datasheet docs/ECHO7_R5_Datasheet.pdf
```

Export verifies the current source/build, rejects a stale SOF and refuses to overwrite an existing ZIP. The archive contains exactly one SOF at the successful build's `firmware/<BUILD_ID>/PartBDebug.sof`. This release file is `firmware/E7070012/PartBDebug.sof`, exported from E12's own successful-build record and original artifact, without using an E11 binary. There is no second `verified/PartBDebug.sof` copy. The bilingual README, project/RTL/test/tool sources, real replay inputs and documentation are retained, excluding build databases, private toolchains and unrelated run caches. The one-page PDF needs no SHA sidecar, and the ZIP receives a CRC check. Dialogue enters the archive only through an explicitly selected, checked export manifest. A fresh clone without a local successful-build record must build before exporting. Archive integrity adds no hardware acceptance claim and performs no Git commit or upload.

| Version with an actual artifact | Isolated build artifact path | Build status |
|---|---|---|
| E7070002 | `build/member_b/20261104T100141_653795Z_build/source/quartus/output_files/PartBDebug.sof` | PASS and programmed, with version-specific board evidence; historical artifact, not the release file |
| E7070003 | `build/member_b/20261104T104155_505074Z_build/source/quartus/output_files/PartBDebug.sof` | PASS and programmed; live bad-frame recovery verified; historical artifact |
| E7070004 | `build/member_b/20261104T111202_124373Z_build/source/quartus/output_files/PartBDebug.sof`; historical artifact | Full Compilation **PASS**; programmed and BCTL version verified at 2026-11-04 22:31:50 AEDT, **PASS**; red2 reselect/new-lock/start observed, and the user confirmed physical stopping when blue1 left the view |
| E7070005 | `build/member_b/20261104T134331_185490Z_build/source/quartus/output_files/PartBDebug.sof`, 6706157 bytes; historical artifact | Full Compilation, post-fit gate, actual programming and E7070005 BCTL readback **PASS**; real blue1 ground task ended NOT_FOUND without docking |
| E7070007 | `build/member_b/20261104T151422_461823Z_build/source/quartus/output_files/PartBDebug.sof`, 6706155 bytes; original historical artifact retained, old release copy replaced | Full Compilation/post-fit, actual programming and BCTL E7070007 readback **PASS**; subsequent real tasks did not complete docking, as retained in trials 01–05 |
| E7070008 | `build/member_b/20261104T160829_127927Z_build/source/quartus/output_files/PartBDebug.sof`; 6706156-byte historical original retained, previous release copy replaced by E9 | Full Compilation/post-fit, actual programming and BCTL E7070008 readback **PASS**; real blue1 board-level DOCKED and zero-speed dwell recorded, user-confirmed continuous forward travel without obvious veering and approximately 335 mm from the probe front at the endpoint |
| E7070009 | `build/member_b/20261104T171519_480274Z_build/source/quartus/output_files/PartBDebug.sof`;6706161-byte historical original retained, old release copy replaced by E10 | Full Compilation/post-fit, actual programming and BCTL E7070009 readback **PASS**; out-of-view blue4 task **INCOMPLETE**, with discovery/lock but no DOCKED within its 60-second observation window. No reverse SEARCH occurred; host STOP completed zero-speed cleanup |
| E7070010 | `build/member_b/20261104T175030_045504Z_build/source/quartus/output_files/PartBDebug.sof`;6706157-byte historical original retained, old release copy replaced by E11 | Full Compilation/post-fit, programming and identity verification PASS; physical out-of-view blue4 NOT_FOUND/SCAN_BUDGET without DOCKED or reverse SEARCH. VISION_ONLY/disarmed/zero cleanup |
| E7070011 | `build/member_b/20261104T182211_444905Z_build/source/quartus/output_files/PartBDebug.sof`; 6706153 bytes; historical build retained, old release copy replaced by E12 | Full Compilation/post-fit, programming/identity and stationary tuning PASS; two physical searches NOT_FOUND and three short comparisons INCOMPLETE. Experimental settings are not baked into the SOF; defaults remain 4/4/5/3/30 |
| E7070012 | `build/member_b/20261104T192605_706632Z_build/source/quartus/output_files/PartBDebug.sof`; `firmware/E7070012/PartBDebug.sof`, 6706156 bytes | Full Compilation/post-fit/programming and stationary pulse PASS; ten physical observations retained: independent near-target DOCKED in trial seven, outside-view trials eight/ten INCOMPLETE; volatile settings are not baked into this default SOF |

The formal course R6 entry remains `./run_all_tests.sh`: clean copy, Verilator **5.050**, module/system self-checks, and CAUGHT for an intentionally broken module. The user's target is ≤285 seconds; the course threshold is 300 seconds. This Windows wrapper invokes the same Bash entry with four compilation jobs. Within one invocation, completely identical compilation inputs share a newly compiled binary through an internal hash cache; all scenarios still run independent assertions, without binaries from an earlier invocation:

```powershell
& $pythonExe tools/run_r6_windows.py --compiler-bin 'C:\msys64\mingw64\bin' --bash 'C:\Program Files\Git\bin\bash.exe' --jobs 4
```

A ModelSim pass is not an R6 pass. Actual version-specific executions in the required environment are listed in the repair record. Run broader historical vision/Python regressions when changes justify them, rather than repeating every old test to increase counts.

The E7070004 formal R6 completed in a clean copy with Verilator 5.050: **219.556074 seconds, exit 0, all 12 items plus CAUGHT PASS, targetMet=true**. Its result is `build/member_b/20261104T110801_416299Z_verilator_course/result.json`. E7070002 took 245.451876 seconds and E7070003 took 221.258456 seconds. Acceleration comes from sharing identical new compilation within the invocation, parallel independent continuous/overload scenarios and four compilation jobs. The 25 fps source rate, assertions and real observation path remain intact; earlier-run binaries and forced observations are not used. The deliberate mutant must still be caught by actual assertions.

E5's first formal R6 is retained as **FAIL, 303.500928 seconds, exit 1, targetMet=false**. Its first 12 items, including the new representative sonar item, passed, but `mainColourSupportReader_tb` compilation reached the complete suite's 300-second deadline; the final item and deliberate-mutant CAUGHT check did not complete. The record is `build/member_b/20261104T133634_057221Z_verilator_course/result.json`.

E5's final formal R6 subsequently completed with fresh compilation of 61 source files: **239.403059 seconds, exit 0, 13 PASS plus 1 CAUGHT, targetMet=true**, meeting the ≤285-second target. The record is `build/member_b/20261104T140614_115616Z_verilator_course/result.json`. This is a separate complete execution, not E4's timing or an accumulation of earlier passing items; the first failure remains intact.

`tb_control_repair` covers one-hot selection, modes, search, settling, safety, negative cases and decoded UART JSON. `tb_board_repair_pins` uses actual NEC pulse timing, a J3 TRIG/ECHO model and 115200 UART without forcing controller inputs. The pixel system chain supplies real perceptionCore pixels; synthetic debug reports and recorded-camera replay are identified separately. Older integration benches used obsolete three-bit selection and fixed ultrasonic behaviour; historical passes cannot be transferred to current code.

E5 targeted evidence is recorded separately. `turn_e5/control_negative.log` passed 269 checks with production TURN_SIGN=−1. The same bench's positive-sign generic comparison passed too; these are not added into 538 independent requirements. Both ModelSim runs plus compilation took 3.367385 seconds. `turn_e5/pixel/` passed 12 reports from the unchanged 12-frame, 25 fps production perceptionCore pixel→C→serialized UART path with the explicit negative sign, taking 84.364643 seconds total (12.529247 compilation, 71.835396 simulation). `sonar_guard_verilator_20261104T133057_380747Z/` passed the full real-clock TRIG/ECHO suite: 46 checks, 12 samples and 11 triggers, taking 89.573 seconds (5.821 compilation, 83.749 simulation). All these paths are under `build/remaining_20261104/`. An older slow ModelSim sonar run was interrupted while the source boundary was reviewed; its INTERRUPTED record is retained and is not a pass. The same sonar bench then gained an explicit six-transaction `+R6_REPRESENTATIVE` entry covering normal range, near range, FAR, no rise, stuck-high/late-fall and recovery, while retaining the complete default boundary path. Formal R6 now includes that representative item and retains its original 12 items and CAUGHT. **Targeted results do not replace E5 full R6 or hardware acceptance; timing closure is established by the separate Full Compilation result.**

The representative sonar entry separately passed 25 checks, 6 samples and 6 triggers over 602 ms of simulation at the production clocks: compilation 5.834637 seconds, simulation 38.076932 seconds, total 43.912875 seconds. Its evidence is `sonar_guard_representative_20261104T133440_446720Z/validated_result.json`. The one-off launcher initially classified the changed PASS-line layout incorrectly; that wrapper's FAIL is retained separately. Validation used the actual exit0 and `PASS ... scope=R6_REPRESENTATIVE` log through the formal R6 pass parser, without rerunning or rewriting the simulation. This representative path is also included in the final complete E5 R6 above.

E6 formal R6 passed one complete run: **266.840318 seconds, exit0, 13 PASS plus 1 CAUGHT, targetMet=true**, using Verilator5.050, four compilation jobs and fresh compilation of 61 source files. The result is `build/member_b/20261104T144856_668139Z_verilator_course/result.json`. This is the same source as the first build rejected for critical timing warnings: its functional simulation met the ≤285-second target, without establishing timing or hardware acceptance. Subsequent actual-path corrections cannot automatically inherit this source's result.

E6's focused control regression passed with production `TURN_SIGN=-1` and generic `+1`: **338 checks and 53 complete UART messages per configuration**. Compilation plus both ModelSim runs took **5.2128905 seconds**, recorded in `build/remaining_20261104/control_e6_20261104T144617Z/result.json`. These are two parameter configurations of the same requirements, not 676 independent requirements.

The E6 real-pixel→perceptionCore→C→serialized UART path passed one independent run, recorded in `build/remaining_20261104/pixel_uart_e6_20261104T144702_631205Z/result.json`: **9.217031 seconds** compilation, **69.766992 seconds** simulation, **78.991060 seconds** total. It used **14 frames/14 reports at fixed25fps**, extending only the original centred segment from 2 to 4 frames to supply three-frame confirmation after the new stopping fence; original frames and assertions were retained. UART counts were search41, left18, forward19, right34 and zero178. The bench shortens dwell to 1 ms; it neither measures mechanical settling nor runs the full board-level 1.5-second dwell, and it does not force internal observations. Full R6 is recorded separately above; focused simulations still do not replace Full Compilation or hardware acceptance.

E7 formal R6 passed one complete run: **265.276162 seconds, exit 0, 13 PASS plus 1 CAUGHT, targetMet=true**, using Verilator 5.050, four compilation jobs and fresh compilation of 61 source files, meeting the 285-second target. Evidence is `build/member_b/20261104T151442_166532Z_verilator_course/result.json`. This is E7's own complete result, not E6's 266.840318 seconds. E7 Full Compilation and actual programming subsequently passed; real task results are recorded separately and cannot be replaced by simulation success.

E7's focused result is `build/remaining_20261104/control_e7_20261104T151338Z/result.json`: all 256 default U values are arithmetically equivalent, and production-negative/generic-positive TURN_SIGN each passed **338 checks and 53 complete UART messages**. Compilation and both simulations took **5.113292 seconds**; this does not count as 676 independent requirements. The first `control_e7_20261104T151306Z/` attempt failed lexical compilation, corrected by adding whitespace; the original failure remains retained. Focused checks do not replace the separate full R6, build or hardware results.

E8's focused control result is `build/remaining_20261104/control_e8_20261104T160731Z/result.json`: production `TURN_SIGN=-1` and generic `+1` each passed **433 checks and 88 complete UART messages**, with 0 compilation errors/0 warnings. Compilation plus both simulations took **6.7496263 seconds**. Coverage includes new far/near, left/right differential steering and the original ALIGN, boundary reconfirmation, control and safety requirements; two parameter configurations do not count as 866 independent requirements.

E8 formal R6 passed one complete run in **270.641086 seconds, with 13 PASS plus 1 CAUGHT and targetMet=true**. Verilator5.050 used four compilation jobs and simulation concurrency 2, compiling 61 source files freshly in a clean copy. Evidence is `build/member_b/20261104T160829_370108Z_verilator_course/result.json`. This is E8's own functional verification, meeting the 285-second target without inheriting E7's result. It does not replace the separately recorded Full Compilation or E8 hardware acceptance.

Within that run, the pixel→real perceptionCore→C→serialized UART path retained the original **14 frames/14 reports at fixed25fps**, target identity and position sequence, without forcing internal observations. PASS counts were search41, left18, forward19, rightCorrection34, zero177, coarseRight34 and rightSpin0; coarseLeft/fineLeft/fineRight were all 0. At actual U160 while already in APPROACH, complete UART messages matched logical forward-right correction 3/5 exactly; an in-place right turn could not satisfy that check. Left differential and near-range 4/3 combinations are covered by the control test, not claimed as exercised by this pixel scene. Stop, three independent frames beyond the fresh capture fence and final STOP assertions remain. The bench's 1 ms dwell still does not establish physical settling over the board's 1.5 seconds.

E9 focused control regression **passed**: ModelSim production `TURN_SIGN=-1` and generic `+1` each completed **696 checks and 245 full UART messages**, with 0 compilation errors/0 warnings. Compilation plus the actual negative/positive simulations took **20.8500433 seconds**. Evidence is `build/remaining_20261104/control_e9_20261104T171519Z/result.json`, covering bounded reverse recovery, shared scan/task time, stopped reconfirmation, original control/safety and complete UART. These two parameter configurations do not count as 1392 independent requirements. The initial host PASS matcher omitted a colon and falsely reported FAIL, retained as `wrapper_result_initial.json` in that directory. The negative-sign simulation passed on its first execution and was not rerun; the same compiled library was used only to run the previously unexecuted positive-sign configuration. This wrapper error is not an RTL failure. E9 keeps the original 14-frame fixed-25-fps pixel fixture, sequence and assertions. Formal R6 subsequently passed independently, as recorded below. Full Compilation/post-fit and programming/identity verification subsequently passed; physical reverse-recovery results are recorded separately.

The 20.8500433 seconds are accumulated execution time for compilation and the two simulator calls, excluding the interval spent correcting the host matcher. The recovery test retains the 150000 logical-microsecond threshold, but the shared test time advances by one per 20 ns clock, UART is accelerated and the dwell is shortened. It verifies logical boundaries and complete messages, not a measured 150 ms physical pin pulse or vehicle settling time.

E9 formal R6 passed one complete run in **274.530007 seconds, exit0, 13 PASS plus 1 CAUGHT, targetMet=true and cleanBuild=true**, meeting the 285-second target. Evidence is `build/member_b/20261104T171630_007376Z_verilator_course/result.json`. The original 14-frame fixed-25-fps pixel test passed unchanged, and the control test also completed 696 checks/245 full UART messages under Verilator. This is E9's own result, not E8's 270.641086 seconds. Full Compilation/post-fit and programming subsequently passed independently. R6 itself does not replace timing or physical reverse-recovery verification.

<a id="hardware"></a>

## 按版本区分的实机证据 / Version-specific hardware evidence

**中文**

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

**English**

The paths below index original logs in this working directory. Full build databases and simulation caches under `build/` are not committed. The portable account is the [repair record](docs/REPAIR_RESULT.md); the release retains only the current SOF and datasheet. A local log absent from a fresh clone is not a new execution result.

| Version and input layer | Observed result | Evidence and scope |
|---|---|---|
| E7070002, synthetic vision→real chassis | U80/U120/U160 produced turning/forward/opposite turning; heartbeat loss revoked authorization and renewal did not restart; the user confirmed wheel movement and stopping | `build/repair/hardware_injection.jsonl`; `hardware_straight.jsonl` includes confirmation that both wheels moved forward; raised chassis |
| E7070002, real IR/J3/UART | A latched stop; first POWER only released it; second new POWER started; real J3 echoes were valid | `build/repair/hardware_ir.jsonl`; not proof of every physical distance boundary or floor stopping error |
| E7070002, physical scene correction | Cropped red1/blue1 caused overflow; moving the same A4 sheet farther away produced 23 locks across 24 distinct frames, blue1 quality 255, and eight-frame calibration 41/24 | `build/repair/live_capture/`, `hardware_vision_e7070002.jsonl`; VISION_ONLY remained at zero speed |
| E7070003, real bad-frame recovery | Historical faultFlags=3 remained; frame 338 regained `sourceHealthyFresh=true` and `targetLockedFresh=true` without reset or clearing the fault history | `build/repair/hardware_recovery.jsonl`; verifies correction of the E2 permanent inhibit |
| E7070003, continuous real vision | 22 locks across 23 distinct frames; frame 855 blue1 quality 255, U115/V186, 122×130 box, 59.478 ms processing | `build/repair/hardware_vision.jsonl`; zero-speed VISION_ONLY, not six-bay floor completion |
| E7070003, real red2 | Request tag 5→6 proved reselect; start preceded the new lock and entered SCAN_UNCALIBRATED/NOT_FOUND, with no automatic revival | `build/repair/hardware_red2_e7070003_early_start.jsonl`; recorded failure, not successful red2 acceptance |
| E7070004, real red2 and real camera | Tag 3→4; frame 2900 acquired the new lock before ARM/ALIGN, logical L+4/R−4 cm/s, real J3=468 mm; scan uncalibrated, failure=NONE and historical faultFlags=3 retained; the user confirmed red2 starting and clarified that it stopped when blue1 left the view | `build/repair/hardware_red2.jsonl`, `red2_console.log`; the host STOP record's DISARMED, L0/R0 and zeroSent=true establish board state/message completion, while its independent physical stopping time was not measured. Final state: VISION_ONLY, disarmed, logical zero speed, with standstill confirmed by the user. |
| E7070004, all six physical blue cards | Same-frame GRAB frame 26844 accepted blue1–6 at quality 255; across another 12 distinct B frames, each blue digit was accepted 12/12, while selected blue1 was C-healthy/locked 12/12; all samples commanded zero speed | `build/continuation_20261104/six_cards_initial/`, `blue1.json`, `vision_findings.json`; red57/blue37, configuration 1, normal perspective; green tape covered red2 and its residual was rejected rather than assigned a false digit |
| E7070004, six physical switch selections and invalid masks | 150.054 seconds, 441 read-only pairs; each one-hot selection produced its matching real blue-card lock; 17 no-selection and 27 conflict samples; all 441 were VISION_ONLY, disarmed, without motion permission and at logical zero speed | `build/continuation_20261104/six_switches.json` and `six_switches_analysis.json`; C healthy 390/441, locked 370/441, B good 434/441; all seven candidate-overflow bad frames and lost locks retained |
| E7070004, physical SW6/7 display | The user confirmed SW6 colour information and automatic alternation between both pages; six candidates left the second page empty, as expected for the slot layout. SW7 showed colour/“no marker” over a white gap, then `ID:B1` after the paper moved so the complete blue1 box covered the centre | See the [repair record](docs/REPAIR_RESULT.md); SW0-only selection was restored. Physical UNKNOWN/rejection-reason display, all 16 slots occupied together and centre ambiguity remain unconfirmed |
| E7070004, synthetic vision plus real J3 docking | 434 status snapshots over 78.931565 seconds; logical +5/+5 at actual 517 mm, +3/+3 at 446 mm, then first DOCKED/disarmed/zero at 347 mm; after moving the reflector away to 534–615 mm, 12 snapshots over 2.194 seconds remained DOCKED/zero | `build/continuation_20261104/dock_hardware_01.jsonl` and `dock_analysis.json`; the user confirmed movement→slowing→stopping→no restart after moving the reflector away; raised chassis, no floor stopping-error claim |
| E7070004, real J3 protective stop/hysteresis/recovery and independent STOP | HOLD03 retained 469 status snapshots over 86.677721 seconds; all six criteria passed with no unverified items; the user confirmed near-stop, remaining stopped in hysteresis, recovery farther away and subsequent STOP | `build/continuation_20261104/hold_hardware_03.jsonl` and `hold_analysis_03.json`; synthetic vision, real IR/J3/UART, raised wheels; direction was not observed in this run and mechanical stopping latency was not measured |
| Reprogrammed E7070004, three static SW8 pairs at 42 cm | 36 normal and 36 bypass pairs, with 72 distinct frames at each of C/B; selected blue1 was healthy/locked throughout, disarmed and at zero speed. Normal accepted each blue digit 36/36; bypass accepted blue2 35/36 and each other blue digit 36/36 | `build/remaining_20261104/sw8_comparison_confirmed.json` and `sw8_analysis.json`; unchanged scene conditions confirmed by the user, with one uncertain reading (reason3) retained; static VISION_ONLY evidence, not floor-level bypass control or image-to-UART latency |

For approximately two seconds after triggering, status was read without sending heartbeats: all 13 samples remained armed with `leaseValid=0`, comprising 7 ALIGN, 4 LOST and 2 ACQUIRE. Including the trigger sample, there were 8 motion-command samples. **This is not two seconds of uninterrupted stable turning**: brief vision loss made the FPGA enter zero-speed reconfirmation. That run's final BCTL snapshot was frame 2959, E7070004, a good frame, blue1 quality 255, U182/V130, a 101×117 box, 47.652 ms processing, and red2 event 7/id 2. The record establishes red2→new-request lock→start and heartbeat-independent INTEGRATED operation. The user physically confirmed starting and clarified that the chassis stopped when blue1 left the view. The host's two-second STOP independently establishes board revocation/zeroSent only; its physical stopping time was not separately measured. The user's observed stop cannot be attributed to host STOP or the later mode1 switch. Final VISION_ONLY readback is disarmed with logical zero speed, and the user confirmed standstill. Six-bay floor docking and mechanical stopping latency are not established by this run.

The later six-switch observation retained 441 distinct B frames and 405 distinct cached C frames. C/B freeze separately; paired frame IDs need not match. C lock counts in the main blue1–6 intervals were 197/200, 22/23, 24/28, 16/22, 23/29 and 26/30; one additional brief blue2 transition was unlocked, and return to blue1 after conflict was 62/64. Of 27 conflicts, 26 formed a sustained stable mask3 interval and one was a mask6 transition. Every no-selection/conflict sample had no C health/lock and no selected B target. The first return-to-blue1 sample retained an old CLEAR report, which C did not accept as a new lock. All seven bad B frames were candidate overflows, each followed by an observed good B frame. For some bad samples, selection changed before relocking was observed. This establishes six-position visual selection coverage, not 441 continuously locked samples or floor-level six-bay completion. See the full interval table and bad-frame indices in the [repair record](docs/REPAIR_RESULT.md). SW6/7 have only the partial display confirmations listed above; the later static SW8 comparison is a separate record, not part of this six-switch result.

The post-reprogramming SW8 pairs used the user-confirmed camera-to-card distance of 42 cm, unchanged placement/lighting and red48/blue20. The first session completed one pair, then timed out waiting for the switch; its original result remains PARTIAL. A new session captured the remaining four stages without repeating or overwriting the first pair. After the operator confirmed unchanged conditions across sessions, the comparator returned COMPARISON_VALID. These 72 pairs are separately frozen C/B samples, not all native camera frames or a claim of matching C/B frame identity. One uncertain blue2 reading in bypass is retained. See the [repair record](docs/REPAIR_RESULT.md) for per-stage results and capture-to-completion times; those times are not image-change-to-UART response times. A chassis resting on the floor while every sample commands zero speed does not establish floor-level closed-loop operation.

After the display checks and repositioning, ground preflight read cfg7, colour-calibrated state, valid J3=386 mm and healthy/locked blue1. It remained VISION_ONLY, disarmed, at zero speed, with no IR emergency stop and a 10-second uncalibrated scan budget. This snapshot read CCTL only, not the new B colour profile, so current thresholds are not inferred; red48/blue20 and the uncalibrated colour state above describe the SW8 sampling window only. This preflight had not started the first ground revolution; subsequent motion results are recorded separately in the [repair record](docs/REPAIR_RESULT.md), with the snapshot at `build/remaining_20261104/ground_preflight_status_01.json`.

The J3 follow-up used synthetic vision, real ranging/IR/UART and raised wheels. The docking record's 517→446→347 mm readings identify first observed state changes, not ruler-calibrated boundaries; criterion confirmation points at 521/454/321 mm came from different, later snapshots. After first DOCKED, all 83 snapshots over 14.853 seconds remained disarmed/zero, including the 2.194-second confirmation after moving the reflector farther away. The user confirmed the physical sequence. Cleanup returned to VISION_ONLY, IDLE, disarmed and zero speed. No floor stopping-distance error was measured.

HOLD03's qualifying hazard window covered 231–242 mm, five snapshots over 0.647892 seconds. Its hysteresis window covered 254–292 mm, seven snapshots over 1.163541 seconds, all HOLD/zero. Moving farther away to 367–407 mm yielded 19 snapshots over 3.119478 seconds of ALIGN with logical −4/+4. At 80.491761 seconds, the host explicitly sent TX4 STOP while continuing the same template and heartbeats. From STOP ACK to the final sample was 6.093588 seconds: all 34 distinct-frame status snapshots were disarmed/zero with zeroSent=true. Their first-to-last sample span was 5.919557 seconds, with the native frameId advancing by 147. Real J3 stayed at 367–376 mm; lease, source and target lock remained valid; sonarHold/IR/fatal stayed false; mode, selection, tag and configuration did not change until the later VISION_ONLY cleanup. The user confirmed near-stop, hysteresis hold, recovery and the subsequent automatic stop, but did not observe wheel direction. These are 34 status polls, not 34 independent sonar measurements. Statements about maintained state describe every recorded sample; this does not measure mechanical stopping latency or establish the separately unobserved STOP timing in the earlier red2 run.

Both previous HOLD records remain. HOLD01 retained 362 snapshots over 66.181 seconds and passed board checks, but the user did not confirm the complete physical sequence and requested a repeat. HOLD02 retained 434 snapshots over 79.899 seconds and its original FAIL: the measured distance left the hysteresis interval before the host's requested one-second observation completed. The final state had reached 313 mm, ACQUIRE and still armed, but the host treated the incomplete stage as failure and immediately sent STOP, preventing observation of resumed motion. The user therefore did not see recovery; this does not establish a production RTL recovery defect. The one-off acceptance script now records NOT_VERIFIED and continues after early safe recovery, producing PARTIAL overall. HOLD03 completed every stage without skipping. Production recovery still requires three new valid readings ≥300 mm; one second is only this test's hysteresis observation requirement. The host correction did not change RTL/SOF, and HOLD03 cleanup completed normally.

Resources/timing remain version-specific: E2 used 29417/32070 ALMs, with worst setup 1.164 ns and hold 0.078 ns; E3 used 29373/32070 ALMs, with worst setup 0.967 ns and hold 0.117 ns. Both used 357/397 M10Ks and 51/87 DSPs, with no unconstrained items and passing four-corner/CDC checks.

**E4 Full Compilation PASS:** 1121.141 seconds, post-fit gate 25.868 seconds, 0 errors and 92 warnings; 29576/32070 ALMs (92%), 41000 registers, 357/397 M10Ks, 51/87 DSPs, 2802640 memory bits and 2 PLLs. Worst four-corner setup is **+1.633 ns**, hold **+0.118 ns**, with no unconstrained items. All 88 checks and coverage of 63 synchronization chains per corner passed; MTBF is NOT_ASSESSED. Programming is recorded in `build/repair/program_e7070004_console.log`, with E7070004 verified through BCTL. Red2 hardware testing is recorded separately: compilation/programming success does not establish motion acceptance.

**E5 Full Compilation PASS:** compilation took 1173.143 seconds and the post-fit gate 25.799 seconds, with 0 errors and 92 warnings; **29507/32070 ALMs**, 40957 registers, 357/397 M10Ks, 51/87 DSPs and 2 PLLs. Worst four-corner setup is **+2.089 ns** and hold **+0.116 ns**. All 88 checks passed, all unconstrained counts are zero, and each corner passed 63/63 synchronization-chain coverage; MTBF remains NOT_ASSESSED. Completion at **2026-11-05 01:03:31 AEDT** is a build timestamp, not a programming timestamp. Evidence is `build/member_b/20261104T134331_185490Z_build/result.json` and `timing.json`. The original SOF was subsequently programmed with E7070005 readback, recorded in `build/remaining_20261104/program_e5_console.log` at UTC2026-11-04T14:11:16.707754 (01:11:16.707754 AEDT the next day), then copied to the release path. Programming success does not establish ground-task completion.

**E6 first Full Compilation acceptance FAIL:** fitting succeeded with **29462/32070 ALMs (92%)**, 41136 registers, 357/397 M10Ks, 53/87 DSPs and 2 PLLs. CLOCK_50 setup slack is **−0.265 ns** at Slow85, with **−1.786 ns TNS**, and **−0.203 ns** at Slow0; worst hold is **+0.120 ns**. The Quartus compile tool took 1183.703 seconds and exited 0, but two critical timing warnings caused gate rejection and the final build result exited 1. Evidence is `build/member_b/20261104T144730_277631Z_build/result.json` and its original STA reports. Functional R6 does not override negative setup. Detailed path diagnosis was subsequently used for E7, which obtained its own successful build. E6 remains a failed, never-programmed historical revision.

The actual STA diagnosis in `build/remaining_20261104/e6_sta_diagnosis_20261104T150928_837210Z/` took **13.098885 seconds** and identified `mode → adapter fence → 32-bit abs → two DSPs → clamp → alignPulseUs`, motivating E7's narrower default arithmetic path. This duration measures diagnostic report generation, **not a passing timing result**. E6's negative setup and unprogrammed status remain; E7's pass comes from its separate post-fit result.

**E7 Full Compilation and post-fit PASS:** compilation took **1147.755 seconds** and the gate **26.087 seconds**, with 0 errors and 92 warnings; **29320/32070 ALMs (91%)**, 41015 registers, 357/397 M10Ks, 51/87 DSPs and 2 PLLs. Worst four-corner setup is **+0.864 ns**, hold **+0.117 ns**; all 88 checks passed, unconstrained counts are 0 and each corner passed 63/63 synchronization-chain coverage. MTBF remains not assessed. Evidence is `build/member_b/20261104T151422_461823Z_build/result.json` and `timing.json`, with an original 6706155-byte SOF. It was then programmed with E7070007 readback, recorded in `build/remaining_20261104/program_e7_console.log` at UTC **2026-11-04 15:34:42.428181** (**02:34:42.428181 AEDT** the next day).

**E8 Full Compilation and post-fit PASS:** `build/member_b/20261104T160829_127927Z_build/` records **1159.722 seconds** compilation and a **25.963-second** independent gate, with 0 errors, 92 warnings and no critical warning. Resources are **29281/32070 ALMs (91%)**, 41081 registers, 357/397 M10Ks, 51/87 DSPs and 2 PLLs. Worst setup is **+1.021 ns**, hold **+0.121 ns**; all 88 timing checks passed, all unconstrained counts are 0 and each of four corners completed 63/63 synchronization-chain coverage. MTBF remains not assessed. Evidence is the directory's `result.json` and `timing.json`. The original SOF is **6706156 bytes** at `source/quartus/output_files/PartBDebug.sof`.

The original successful E8 artifact was actually programmed with BCTL E7070008 readback. `build/remaining_20261104/program_e8_console.log` records UTC **2026-11-04 16:28:58.446132** (**03:28:58.446132 AEDT** the next day). After confirming applicability on the same plastic floor, `e8_scan_calibrated_13600ms.json` reads back the 13.6-second scan calibration in VISION_ONLY, disarmed and at zero speed. All four pairs in `e8_blue1_centre_preflight.json` locked real blue1 at U123, with actual J3 687–690 mm. These establish programming, budget restoration and zero-speed preflight. The following real blue1 task's board-level DOCKED and physical-confirmation scope are recorded separately; preflight alone does not establish docking.

After programming E7, the 13.6-second budget was restored after confirming the same plastic floor, power setup and unchanged SEARCH 4 cm/s. `build/remaining_20261104/e7_scan_calibrated_13600ms.json` reads `scanBudgetUs=13600000`, `scanCalibrated=true` and `scanBasis=CALIBRATED_TIME`: VISION_ONLY, disarmed, L0/R0, zeroSent=true, IR=false, valid J3=694 mm, with a healthy real source and target NOT_FOUND. This is a post-programming zero-speed/budget snapshot. The later KEY0 resets and real trials 01–05 are recorded below; this snapshot itself does not establish alignment or docking success.

E5's post-programming zero-speed hardware records are both VISION_ONLY. `build/remaining_20261104/e5_zero_scene_01.json` retains 8 complete C/B pairs, each side with 8 distinct frames: selected blue1 healthy/locked 8/8, zero speed throughout, calibrated colour configuration1, red24/blue16. The later `e5_far_01.json` retains 6 real open-space pairs, all with `distanceMm=4000`, `distanceValid=true`, `distanceKind=FAR`, `sonarHold=false` and `zeroSent=true`; the user explicitly confirmed ` FAr` on the distance page. The FAR window was source-healthy but target-locked 0/6, so it is not reported as blue1 tracking. C/B are frozen separately, without a same-native-frame claim; FAR is a sentinel, not a measured four metres. This verifies the new firmware's open-space readings and display, with the subsequent three ground revolutions recorded below and six-bay motion still incomplete.

E4's first ground run, `ground_scan_01.jsonl`, was TRIAL_INVALID: 78 snapshots over 21.518290 seconds, with 12 moving SEARCH snapshots at logical −4/+4. After 2.899142 seconds of accumulated SEARCH command time, actual `4000,false` produced HOLD/zero/zeroSent before host cleanup STOP; cleanup had no errors. The user observed approximately 75 degrees before it stopped and confirmed clockwise rotation viewed from above. The current surface was corrected to **plastic flooring**: the earlier “epoxy” statement remains in the raw log but is not accepted as epoxy-floor evidence. No complete revolution or scan calibration was obtained, and a full-circle duration is not extrapolated from 75 degrees. The later body-left/right-to-U observations motivated E5's turn correction. New FAR semantics follow the user's subsequent requirement and do not rewrite the old E4 failure.

E5 has **3/3 physically confirmed complete-revolution observations**, all on the current plastic floor at logical +4/−4, without HOLD. Records are `build/remaining_20261104/ground_e5_01.jsonl`, `ground_e5_02.jsonl` and `ground_e5_03.jsonl`. Times below are accumulated SEARCH command time; FAR counts are moving-state snapshots, not independent ultrasonic samples.

| Trial | SEARCH time | Moving snapshots / FAR subset | Physical observation reported by the user |
|---|---:|---:|---|
| 1 | 13.561176 s | 80 / 10 | Anticlockwise full revolution, approximately 10° overshoot and 3.5 cm forward displacement; one-sided surge at startup |
| 2 | 11.075500 s | 66 / 13 | Full revolution, approximately 5° overshoot and 2 cm forward displacement; one-sided surge at startup |
| 3 | 11.436358 s | 70 / 15 | Full revolution; the user reported pressing A late, with approximately 45° overshoot; no one-sided startup surge, displacement not supplied |

The observed time range is **2.485676 seconds**. Stops include operator response and overshoot, so they are not precise 360-degree timing; the angular error of an automatic stop at a fixed 13.6 seconds has not been tested. Trial1 retained 197 snapshots over 34.960365 seconds, with healthy source/lease/valid J3 throughout motion, 70 measured-range snapshots at 377–3120 mm and a longest observed FAR window of 1.072009 seconds. IR A revoked ARM and commanded zero before host STOP, followed by VISION_ONLY, IR latched and zero speed. Anticlockwise motion confirms the direction correction. The first two trials' one-sided surge and translation remain observed mechanical/drive behaviour with the cause unisolated; equal commanded wheel speeds do not establish simultaneous wheel startup.

The largest observed command time was rounded up to **13.6 seconds** and actually written. `e5_scan_calibrated_13600ms.json` reads `scanBudgetUs=13600000`, `scanBasis=CALIBRATED_TIME` and `scanCalibrated=true`, with VISION_ONLY, disarmed, IR latched, L0/R0 and `zeroSent=true`. This supports bounded approximate scanning on the current floor, without guaranteeing exactly 360° on future runs. The laboratory epoxy floor needs its own measurement. Reprogramming clears the session setting; after confirming that the same surface, chassis and wheel-speed conditions remain applicable, 13.6 seconds can be restored without repeating three revolutions merely to count progress. The subsequent real blue1 failure is recorded below; six-bay completion remains outstanding.

E5's real-camera blue1 ground task, `build/remaining_20261104/integrated_blue1_01.jsonl`, retains 656 status snapshots and approximately 36.330 seconds of task observation. The first ACQUIRE occurred about 1.2 seconds after starting but failed post-settle target confirmation. Search continued until approximately 11.2 seconds of accumulated SEARCH, when a second ACQUIRE led to ALIGN. There were then 9 ALIGN windows and 8 LOST windows, with only 5 APPROACH snapshots at measured ranges of 613–663 mm. At 13.6 accumulated SEARCH seconds, the controller automatically entered `NOT_FOUND/SCAN_BUDGET`, disarmed and commanded zero: **this was not DOCKED**. The user observed the first pass failing to retain the target, followed by tracking/approach on the second pass, left-right oscillation and turning away. This CCTL-only record has no continuous BCTL U trace, so all loss events cannot be attributed to coordinate sign.

The subsequent `real_turn_probe_e5_01.jsonl` remains **INCOMPLETE**: only 2 of the required 3 post-stop locked frames were obtained. With a fixed blue1 card, pre-turn U was 57,57,57. The start-to-host-STOP-request interval was approximately 0.340987 seconds, with 7 correct ALIGN snapshots commanding logical +4/−4 and no cleanup errors; this interval is not a measured wheel-motion duration. The earliest VISION_ONLY/zeroSent FPGA timestamp was 1542683620 µs. Relative to it, subsequent actual captureStart values were +245.133 ms at U96/locked, +525.021 ms at U142/unlocked and +884.877 ms at U169/locked. A separate six-frame observation at +90.489–92.608 seconds recorded stationary U173. The user confirmed that the paper stayed fixed and the wheels eventually stopped, without timing the residual turn. U initially moved toward centre, then overshot; image position continued changing beyond 200 ms. These sparse observations do not determine exact mechanical stopping time, and the candidate 1.5-second dwell is not a measured settling result.

E7 hardware runs now retain both CCTL and BCTL with `--with-vision`; original records and operator feedback are summarized in `build/remaining_20261104/e7_operator_notes.json`. The local `integrated_task_observer_e7.py` checks the E7 build and, by default, sends no START, heartbeat or synthetic observations. Trials 01–03 recorded physical POWER; trials 04–05 separately used one explicit HOST START with the real camera and cannot be described as remote-control start verification. Full BCTL reads target an approximately 0.2-second interval, with actual spacing depending on JTAG read time. Each read retains start/end timestamps; C/B freeze separately without a same-frame claim, and sparse polls may miss short states. Every run retains its own deadline reason and STOP→VISION_ONLY cleanup.

| E7 actual window/trial | Recorded result | Physical feedback and interpretation limits |
|---|---|---|
| Trial 01, POWER | `integrated_blue1_e7_01.jsonl`: all 147 C snapshots IDLE/zero; start window expired, INCOMPLETE | User: “按了power，没反应” (pressed POWER, no response), then “按了好多次，没反应，然后重启后动了一下又不动了。再次重启后又动了一下。” (many presses, no response; after each of two resets it moved briefly), identifying KEY0. Without contemporaneous IR/motion traces, the cause of that movement and exact button timing remain unproven. |
| Post-KEY0 check | `e7_after_key0_pairs.json`: C healthy 5/6 pairs, one candidate-overflow frame followed by recovery; J3 progressed from 92 mm/HOLD to 792 mm/HOLD, then 788 mm/clear | KEY0 restored INTEGRATED/disarmed and the default uncalibrated 10-second budget. After E7 verification, VISION_ONLY/zero and clearing the area, `e7_scan_restored_after_key0.json` read back 13.6 seconds again. |
| Trial 02, POWER | `integrated_blue1_e7_02.jsonl`: first observed ARM at host 20.038747 s, 261 C/258 B, task observation 60.015279 s; SEARCH→ACQUIRE→SEARCH→215 mm HOLD→319 mm SEARCH→33 mm HOLD, then approximately 251 mm held; accumulated SEARCH 4.512126 s, deadline INCOMPLETE | User: “扫过了蓝1，继续转的时候，遇到了线缆缠绕，然后超声波判定到距离过近中止” (passed blue1, then cables tangled while turning and near-range protection stopped it). All sampled B frames were good/NOT_FOUND without overflow; no sampled ALIGN, APPROACH, DOCKED or blue1 lock. This establishes actual start and near-range interruption, not docking. |
| Trial 03, POWER | `integrated_blue1_e7_03.jsonl`: 140 C/138 B; the 45-second start window expired during a B read, no ARM, INCOMPLETE | User: “按了很多次power，都没反应” (pressed POWER many times without response). There is no exact IR-reception/button timestamp; neither an IR hardware failure nor precise button/window ordering is inferred. |
| Trial 04, one HOST START | `integrated_blue1_e7_04.jsonl`: preflight 4/4 distinct locked blue1 frames, U112, J3 698–699 mm; 206 C/201 B over 60.1635664 s of task observation; APPROACH +5/+5 followed by repeated short ALIGN/ACQUIRE, ending J3 684 mm; no DOCKED, INCOMPLETE | User: “车刚刚在向前蠕动，有点像往前走，但是右轮蠕动幅度明显更大” (creeping forward with much more right-wheel movement); “左轮基本没动，就只动了一点点，大概1cm，右轮动了3.5cm” (left barely moved, approximately 1 cm; right 3.5 cm). These are reported net wheel travel over the whole trial, including initial straight travel, not displacement per pulse. |
| Trial 05, one HOST START | `integrated_blue1_e7_05.jsonl`: preflight 3/3 distinct locked frames, U197, J3 669 mm; 56 C/51 B over 15.048011 s; U197→193→186→132→123, then after APPROACH U80→60→56; all sampled B frames good, one transient unlocked sample; no DOCKED, INCOMPLETE | User: “有转进，但更多是左轮大幅度动作，右轮基本没动。现在蓝一变到左1/3了” (turned inward, mainly large left-wheel movement, right barely moved; blue1 now in the left third). Short 4 cm/s turning initially brought the target toward centre, then across it; no complete physical wheel-speed or per-pulse trace was obtained. |

All runs completed STOP and VISION_ONLY zero-speed cleanup without cleanup errors. No observed ARM in windows 01/03 does not erase the user's reported movement outside those windows, and neither an ACK nor a verbal button report supplies a missing start timestamp. Trials 04/05 sent no synthetic reports or host heartbeats and explicitly retain their single host-start provenance.

`ground_straight_e7_2s_01.jsonl` is a separate two-second isolation trial using **centred synthetic vision with real C/J3/IR/UART and an injection lease**, not real-camera docking. Logical speeds were first +5/+5, then +3/+3 below 500 mm. J3 changed from 618 to 454 mm in the loop, read 436 mm at the first cleanup zeroSent and 430 mm later; final state was VISION_ONLY, disarmed, with zero-speed message completion. The user said, “往前走，我看基本是直的” (moving forward; it looks basically straight). This establishes that continuous straight commands can produce relatively straight forward travel in this setup. It does not establish identical wheel speeds, the cause of short-start asymmetry or an E8 repair pass. The contrast between short corrections and continuous straight travel motivates E8's candidate continuous forward steering.

E8's first real blue1 task, `build/remaining_20261104/integrated_blue1_e8_01.jsonl`, completed as **DOCKED_OBSERVED**, retaining 116 CCTL and 110 BCTL snapshots. It began with the pre-locked blue1 and used one HOST START, real camera and real J3/IR/UART, without synthetic reports or host heartbeats. First observed ARM was at host 2.169262 seconds and first DOCKED at 31.484328 seconds, a **29.315066-second** difference between sampled timestamps rather than an exact internal transition delay. At DOCKED, J3 read 329 mm and U110. The following approximately 3.18-second dwell remained disarmed at logical zero with zeroSent=true, passing this run's board-state dwell check; STOP→VISION_ONLY cleanup had no errors. The user said, “持续向前，不明显偏转，左轮大概多走了1cm？探头前端距离大概33.5cm” (continuous forward travel, no obvious veering; perhaps the left wheel travelled about 1 cm farther; approximately 33.5 cm from the probe front). This confirms continuous travel and an approximately 335 mm endpoint. The additional left-wheel centimetre is an explicitly uncertain whole-trial estimate, not precise wheel odometry or displacement per correction. J3's 329 mm and approximately 335 mm measured from the probe front are readings obtained by different methods in this trial; their approximately 6 mm difference does not establish sensor accuracy or justify changing its conversion. Final alignment/reconfirmation still took about 25 seconds, and mechanical stopping time was not separately measured. This trial did not start with the target outside the view. The subsequent blue2 red2 trial and operator observations are recorded below within their separate evidence scopes; they do not combine into six-bay complete search-to-dock acceptance.

E8 blue2 evidence is retained in two separate parts. The first, `build/remaining_20261104/integrated_blue2_e8_red2_01.jsonl`, returned **DOCKED_OBSERVED**, with 99 CCTL and 96 BCTL snapshots, no host START, no synthetic reports and no heartbeat. Red2 event7, a new request, relock and ARM were recorded. Every C snapshot had logical zero speed and motionPermit=false: 82 IDLE, 5 ACQUIRE and 12 DOCKED, with no APPROACH. J3 changed from approximately 633 mm to 295 mm before directly satisfying DOCKED conditions. The window therefore establishes the red2 start chain and board terminal state, **without recording an actual forward command or proving motion-to-dock within that window**. The original result name is retained without adding motion solely because it contains DOCKED.

The second part occurred after that observer had ended. The user reset with KEY0, overlapped red2 with red1, then reported forward travel followed by stopping and an approximately 40 cm ruler estimate. Hands and paper may have affected the contemporaneous distance; no continuous log covers this motion. The initial read in `build/remaining_20261104/e8_blue2_after_operator_key0.json` verified E7070008, physical digit2, DOCKED/disarmed, L0/R0, zeroSent=true, actual valid J3 342 mm and locked blue2. B retained event7/id2, U141 and a 144×159 box, compared with an earlier approximately 87×97 box. This was a new KEY0 session: event numbers are not joined to the previous run as one sequence, and post-terminal U/box changes do not reconstruct the DOCK decision frame or precise chassis displacement. The file ends with VISION_ONLY, disarmed and zero speed; the applicable 13.6-second scan budget was restored separately afterward. Blue2 therefore has **physical travel/stopping feedback and a later terminal-state corroboration**, without a full-motion telemetry claim. The approximately 40 cm estimate and 342 mm reading are not subtracted to claim precise stopping error, and these data do not establish that red1 or a particular unrecorded instant caused motion.

E8's blue3 physical-POWER trial, `build/remaining_20261104/integrated_blue3_e8_power_01.jsonl`, retained **257 CCTL and 254 BCTL snapshots**, with no host START, synthetic reports or host heartbeats. First observed ARM was at host 61.5772666 seconds and first DOCKED at 77.3039882 seconds, a **15.7267216-second** difference between sampled timestamps. Actual J3 was 321 mm at DOCKED. The following 11 DOCKED snapshots spanned 3.127523 seconds, all disarmed with L0/R0 and zeroSent=true, before error-free VISION_ONLY cleanup. At approximately 80.119 seconds, J3 briefly read 167 mm with sonarHold=true; the next snapshot at 80.431 seconds read 308 mm with hold=false. The controller stayed DOCKED/disarmed and did not resume travel. The run must not be described as entirely free of a protective HOLD condition. The 12 nonzero APPROACH snapshots comprised logical 5/5 twice, 3/5 four times and 3/4 six times, with approach ranges 656→500→334 mm. SEARCH did not occur. This run therefore covers real-camera approach, slowing, differential correction, docking and physical POWER starting on E8. All 254 B snapshots were good and fresh, without candidate overflow/error; 253 were locked, with the sole unlocked result being initial ACQUIRING under the new tag. The final B snapshot was good/locked at U128. The user said, “稳定向前，最终距离大概31cm” (steady forward travel, final distance approximately 31 cm). That is an approximate field estimate; comparing it with 321 mm does not establish precise stopping error. This trial also did not start with the target outside the view.

E8 blue4, `build/remaining_20261104/integrated_blue4_e8_host_01.jsonl`, completed as **DOCKED_OBSERVED**, retaining 99 CCTL and 93 BCTL snapshots. It used one HOST START, without synthetic reports or host heartbeats. First ARM was at 2.1602634 seconds in ALIGN with logical −3/+3 and J3 655 mm; at 7.300 seconds APPROACH requested 5/5 at 642 mm, at 8.043 seconds 5/3 at 585 mm, at 9.260 seconds 4/3 at 487 mm, and at 11.206 seconds ACQUIRE requested zero at 334 mm. First DOCKED was at 28.2996343 seconds and 316 mm. The first-observed ARM-to-DOCKED interval was **26.1393709 seconds**. Near-target stopping, reconfirmation and final short corrections took approximately **17.1 seconds**, not continuous turning time. The following 11 terminal snapshots spanned 3.27686 seconds, all with J3 316 mm, disarmed, logical zero and zeroSent=true; VISION_ONLY cleanup completed without errors.

All 93 B snapshots were distinct frames, good/fresh/observed/locked, without candidate errors or overflow. The box grew from 84×94 to 157×172; U moved from 132 through a minimum 77 to a final 111. No HOLD, IR, LOST or SEARCH was observed. The user said, “启动的时候有抽动，然后偏右。直着向前接近后。停止，最后短向左修，修回居中（虽然还是有点偏右），最终停车距离大概32cm” (a jerk at startup, then drift to the right; straight approach, stopping and a short left correction back toward centre, though still slightly right; final distance approximately 32 cm). Startup jerk, rightward drift and residual rightward position therefore remain observed limitations. Yaw error is not claimed eliminated and actual wheel speed was not measured; approximately 32 cm is the user's field estimate.

The user then explicitly said, “我觉得5/6都不用单独测了，1-4已经说明了性能” (separate 5/6 trials are unnecessary; 1–4 have shown the performance). Separate blue5/6 ground trials are therefore cancelled for this run. Static recognition and physical-selection evidence for all six blue cards remains, without relabelling 5/6 as passed ground tasks. The subsequent single initially-out-of-view blue4 search-to-dock trial was executed and failed with NOT_FOUND, as recorded below. No further per-card expansion is planned; the next step is the user-requested E9 bounded reverse-recovery candidate.

E8's initially-out-of-view blue4 search, `build/remaining_20261104/integrated_blue4_e8_search_01.jsonl`, retained **153 CCTL and 150 BCTL snapshots**. Physical POWER started the task, with no host START, synthetic reports or heartbeats. First ARM was observed at 22.954783 seconds with SEARCH requesting logical +4/−4. At the first ACQUIRE at 24.568753 seconds, C frame24263 reported observed=true but not locked, with zeroSent already true and accumulated search of 1.586529 seconds. It returned to SEARCH at 26.999764 seconds without securing the lock, then recorded near-range HOLD at 31.709/34.006 seconds. After the user removed the obstruction, FAR allowed search to resume at 41.016 seconds. At 46.869 seconds, accumulated active SEARCH reached 13.6 seconds and entered final ACQUIRE; at 49.422 seconds it automatically entered **NOT_FOUND/SCAN_BUDGET**, disarmed and commanded zero. VISION_ONLY cleanup completed without errors. There was no ALIGN, APPROACH or DOCKED: **this initially-out-of-view search-to-dock trial failed**. A transient observed target is not a sustained lock; time spent in near-range HOLD does not consume the 13.6-second active-search budget.

The user said, “我移开了障碍物，其继续搜寻。其扫过蓝4两次，但都未锁定。是不是扫过速度太快处理不过来” (I removed the obstruction and it resumed searching; it passed blue4 twice without locking; could it be moving too fast for processing?). This retains the physical two-pass failure, recovery after obstruction removal and the question about speed/processing. A unique cause has not been established, and the question is not presented as a proven throughput bottleneck. The earlier pre-locked blue4 approach/docking success and this search failure remain separate results; neither substitutes for the other. The user subsequently requested a slow/small-step reverse sweep after the target had been seen but passed while stopping. This was accepted as E9, without new per-card expansion or claiming that an unverified candidate repaired the E8 failure.

Read-only review of this E8 failure does not support a simple processing-throughput interruption. The 150 sampled distinct B frames were all frameGood/fresh, with processing latency 38.819–45.892 ms and capture age at snapshot 39.587–84.890 ms. BufferDrop stayed at historical value 3, completion discard was 0, and current overflow/error/overrun/transportSticky were all 0; sampled C source health remained true during the task. Sparse B reads saw 149 NOT_FOUND and one REQUEST_CHANGED, missing C frame24263's transient acceptance. This cannot be described as never recognizing the target or observing every native frame. Relative to the earliest C zeroSent, later newly captured rejected-candidate box centres were approximately U155 at +303.352 ms, U215/clipped at +583.240 ms and U218 at +863.128 ms, compared with U65 at −16.520 ms beforehand. These centres use native bbox y, not locked-report coordinates. Reason4 combines orientation/anchor-orientation and shape rejection; reason3 means uncertainty. New images moving after zero-message completion support the observed target passing beyond the view, without measuring mechanical settling or establishing the respective contributions of inertia, positioning and recognition variation.

**E9 Full Compilation and post-fit PASS:** `build/member_b/20261104T171519_480274Z_build/` records **1218.109 seconds** for compilation and **26.779 seconds** for the gate, with 0 errors, 92 warnings and no critical warning. Utilization is **29699/32070 ALMs (93%)**,41206 registers, 357/397 M10Ks, 2802640 memory bits, 51/87 DSPs and2 PLLs. Worst setup/hold across four corners is **+0.629/+0.117 ns**; worst recovery/removal is **25.712/0.433 ns**. All 88 report-gate checks passed, with illegal/unconstrained items at zero. Synchronizer coverage is 63/63 at every corner; MTBF remains unassessed. writeGray/readGray/timeGray cover 9/9/32 bits; resultToCamera1589 bits, requestCdc22 bits and resultToDisplay979 physical endpoints have complete expected coverage. Minimum max-skew/net-delay constraint slack is **17.730/11.957 ns**; these are margins, not measured propagation delay. Build completion was **2026-11-04 17:36:05.089257 UTC**, and the original SOF is **6706161 bytes**.

The original E9 SOF was actually programmed: `program_e9_console.log` records `buildIdVerified=true` and completion at **2026-11-04 17:36:35.545149 UTC** (04:36:35 AEDT next day). VISION_ONLY/disarmed/zero was established, and `e9_scan_calibrated_13600ms.json` restored the applicable same-floor 13.6-second budget. All 4 independent C/B pairs in `e9_blue4_calibration_preflight.json` were healthy and locked on blue4 at U125/J3663–664 mm, with cfg1 calibrated, SW3 alone, no IR/HOLD and zeroSent=true. A separate out-of-view preflight had 4/4 healthy NOT_FOUND pairs and J3 about 696 mm. These are preparation checks, not proof of search/recovery/docking. Files are under `build/remaining_20261104/`.

### E9蓝4画外搜索：发现/锁定通过，任务未完成，回扫未触发 / E9 out-of-view blue4 trial: discovery/lock observed, task incomplete, reverse recovery not triggered

**中文**

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

**English**

`build/remaining_20261104/integrated_blue4_e9_search_01.jsonl` retains **650 CCTL and 84 BCTL snapshots**. Physical POWER started the run, with zero host START commands, synthetic reports or host heartbeats. First ARM was observed at host **30.3643098 seconds**. The observer allowed approximately 60 seconds; the observer recorded a task-observation duration of **60.0274842 seconds**, followed by an explicit host STOP. This is neither expiration of the production 120-second task deadline nor scan-budget exhaustion or autonomous DOCKED. The final snapshot at **90.445834 seconds** was VISION_ONLY, disarmed, L/R zero, zeroSent=true and J3 663 mm, with `cleanupErrors=[]`.

| Host observation time (seconds) | Board evidence and scope |
|---|---|
| From 30.3643098 | Normal SEARCH requested logical +4/−4, accumulating **1.441116 seconds** of permitted search requests |
| 31.971505 | Entered stopped ACQUIRE confirmation |
| 32.098617 / 32.225489 | targetObserved and targetLocked were respectively sampled; scanElapsed did not increase afterwards |
| 81.404994 / 81.514565 | Only two APPROACH snapshots, requesting +5/+5; these do not measure continuous wheel travel or displacement |
| 81.786688 | LOST with zero request, then ACQUIRE again; no DOCKED was reached |
| Observation-window end | Host STOP performed cleanup while failure remained NONE; this was not autonomous successful docking, and the hardware task is **INCOMPLETE** |

All 442 task C snapshots had sourceHealthyFresh=true and valid J3, without HOLD, IR or fatal faults. State samples were SEARCH10, ACQUIRE413, ALIGN16, APPROACH2 and LOST1; these counts are not action or pulse counts. **No reverse SEARCH occurred, so this run did not trigger E9's new recovery branch.** ALIGN turning in the opposite direction is not verification of reverse-search recovery. J3 varied within 656–705 mm and did not establish a terminal docking distance.

All 84 B snapshots were fresh/good, without new drops, candidate overflow, overrun or transport faults, at cfg1 and red45/blue28. The task contained 57 B snapshots: 54 locked and three NOT_FOUND. Sampled U progressed from 134→142→a long plateau near 154→133→119, briefly rejected with reason4, then reached 69/66. This supports repeated alignment and crossing the centre after successful discovery; it does not establish a simple throughput interruption. Sparse polling does not cover every native frame or measure exact wheel speed or mechanical stopping time.

The user's physical observation was: “停转的时候几乎正中，但是继续逆时针修后反而有点偏右边。最后顺时针反修，反而又偏左了” — almost centred when scanning stopped, then additional anticlockwise correction moved it right, and clockwise correction moved it left. ALIGN delay/overshoot therefore remains unresolved, and this version has not completed search-to-dock from outside the view. The next revision targets this physical problem without repeating the cancelled blue5/6 trials. Earlier E8 pre-locked-target docking and E9 simulated recovery coverage do not establish this trial's success.

### E10：放宽居中与直接进入前进纠偏 / E10: wider centring and direct forward steering

**中文**

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

**English**

E9 found and locked blue4, but repeated pivots did not complete docking during its 60-second observation window. The user observed correction crossing the centre and overshooting back, then explicitly accepted a wider centring tolerance. E10 therefore changes default `ALIGN_LOW/HIGH` from 110/130 to **90/150**, retaining target identity, lock and safety requirements. U coordinates, camera mapping, perception, switch selection and real J3 input are unchanged.

| E10 default horizontal target position and range | Behaviour after fresh-lock and safety qualification |
|---|---|
| U90–150, range > 500 mm | Forward +5/+5 cm/s |
| U90–150, 350 < range ≤ 500 mm | Forward +3/+3 cm/s |
| U90–150, range ≤ 350 mm | DOCKED and task disarm when the original safety conditions pass; the ≤250 mm hazard protection still takes priority |
| U75–89 or 151–165, range > 500 mm | Forward differential 5/3 or 3/5 cm/s; with production negative TURN_SIGN, low U uses 5/3 and high U uses 3/ 5 |
| U75–89 or 151–165, 350 < range ≤ 500 mm | Forward differential 4/3 or 3/4 cm/s |
| Outside U75–165, or range ≤ 350 mm while outside U90–150 | Cancel forward motion, complete stop/reconfirmation and use the original short ALIGN pivots; the forward-steering corridor does not permit off-centre near-range docking |

At START with an already fresh locked target, or after ACQUIRE has completed zero-speed UART, 1.5-second dwell, a fresh capture fence and three-frame confirmation, range > 350 mm and U75–165 can enter APPROACH directly. Discovering a target during normal search still requires stopped confirmation; a single observed frame does not bypass the lock. The new default ±30 centred band contains the former 3 cm/s fine-pivot region, so default operation no longer pivots within that error range. Larger errors still use 4 cm/s short pivots and the existing 20–100 ms logical duration calculation. The former strict U110–130 band remains a parameter-compatibility case rather than E10's default.

Consequently, E10's far-range injection examples `x=80/160` should produce forward 5/3 and 3/5 correction respectively, or 4/3 and 3/4 at 350–500 mm; opposite wheel directions are no longer the correct expectation for those examples. `x=120` requests equal forward speeds. These expectations apply to E10 and untuned E11 defaults at tolerance30; with the current experimental tolerance40, U80/160 are centred and request equal forward speeds. Historical E9 results retain their strict centring behaviour. E9's bounded reverse recovery, shared 13.6-second scan budget, 120-second task deadline, IR/J3/FAR, source health/freshness, lease and cancellation conditions remain.

The original 14 fixed-25-fps synthetic pixel-layer frames and sequence are retained, through the actual production core rather than a physical-camera recording. The pixel-to-UART test changes the initial U80 expectation to production-default 5/3 forward steering and adds a no-ALIGN check for that segment; the E10 pixel-to-UART result has now passed within formal R6. A wider accepted band is a user-approved behavioural tradeoff, not a measurement of lateral docking accuracy or a fix for mechanical asymmetry. Focused control regression has passed independently. Formal R6 has also passed independently. Full Compilation/post-fit and actual programming/identity verification have also passed. The physical search-to-dock run ended NOT_FOUND/SCAN_BUDGET after brief APPROACH and loss/resumed search; its failure is recorded separately.

**E10 focused control regression PASS:** `build/remaining_20261104/control_e10_20261104T175106Z/result.json` records one ModelSim compilation and three passing configurations, with 0 errors/0 warnings, **29.1663517 seconds** total and no failed attempt. Default U90–150 with production `TURN_SIGN=-1` and generic `+1` each passed **804 checks/275 complete UART messages**, comprising 113 spin, 41 drive and 121 zero messages. fineLow/fineHigh are both 0 as expected from the wider band; forward differential coverage remains steerLow12/steerHigh10 and fineSteerLow2/fineSteerHigh2. A separate explicit legacy U110–130, negative-sign compatibility case passed **817 checks/278 UART messages**, including fineLow8/fineHigh3. These parameter configurations and check counts are not additive independent product requirements. `commands.json` and negative/positive/legacy_band logs remain in the same directory.

This verifies default boundaries, direct APPROACH and retained safety/recovery logic; it does not measure mechanical settling, wheel speed or docking accuracy. Production source and tests are frozen. Formal R6 independently passed in 271.31444 seconds, followed by passing Full Compilation/post-fit in `build/member_b/20261104T175030_045504Z_build/` and actual E10 programming. Hardware outcomes are recorded separately.

**E10 formal R6 independently PASS:** `build/member_b/20261104T175201_822030Z_verilator_course/result.json` records one complete run in **271.31444 seconds, exit0, 13 PASS plus CAUGHT for the intentionally broken lock mutation, targetMet=true and cleanBuild=true**, meeting the 285-second target. Verilator5.050 used 61 fresh source files, four compilation jobs and at most two simultaneous simulations. E9 timings and simulation conclusions were not reused. Production-default control passed 804 checks/275 complete UART messages within this suite.

The same run's `tb_pixel_uart_repair/simulation.log` retains **14 frames/14 reports at fixed25fps**, passing pixel-layer scenes through the actual production perceptionCore, C controller and serialized UART. The input is synthetic marker pixels, not a physical-camera recording or forced internal observed flags. Counts are search41,leftCorrection18,forward79,rightCorrection34,zero116 and leftSpin/rightSpin both 0. Initial U80 forward 5/3 and U160 forward 3/5 steering satisfy the new default entry behaviour; coarseLeft/coarseRight are 18/34, with fineLeft/fineRight both 0. This pixel scene does not establish near-range 4/3 combinations, which the separate control test covers; UART/state assertions do not measure wheel motion. These are E10 RTL_SIM results. Full Compilation/post-fit and actual E10 programming subsequently passed, with stationary calibration preflight complete. This run's physical search-to-dock result is NOT_FOUND/SCAN_BUDGET; its failure and user observations are recorded separately.

### E10独立完整构建、下载与零速校色 / E10 independent Full Compilation, programming and stationary calibration

**中文**

`build/member_b/20261104T175030_045504Z_build/result.json`最终 **PASS**：Full Compilation **1260.493秒**、独立post-fit门检 **25.832秒**，0错误、92警告、0 critical warning；63个构建源文件与当前冻结源码核对一致。器件使用 **29249/32070 ALM（91%）**、40840寄存器、357/397 M10K、2802640存储位、51/87 DSP、2/6 PLL。四角16项setup/hold/recovery/removal检查最差分别 **+0.909/+0.118/+26.947/+0.401 ns**；报告门检88项，非法及所有未约束计数均0。四角同步链各63/63覆盖PASS，MTBF仍未评估。writeGray/readGray/timeGray为9/9/32位全覆盖；resultToCamera1588、requestCdc22及resultToDisplay979物理端点完整覆盖。max-skew/net-delay最差约束裕量分别18.498/13.844 ns；它们是裕量，不是实测传播延迟。

构建完成UTC **2026-11-04 18:11:56.936771**。原始SOF位于该构建目录的`source/quartus/output_files/PartBDebug.sof`，**6706157字节**；`build/remaining_20261104/program_e10_console.log`记录实际program与E7070010身份读回 **PASS**，完成UTC **18:12:33.831751**（AEDT次日05:12:33.831751）。这来自E10自己的构建及下载，不是借用E9 SOF或时序结果。

下载后切至VISION_ONLY、未ARM、零速，并明确恢复同一适用场地的13.6秒扫描预算。`e10_blue4_calibration_preflight.json`中4/4独立C/B样本均健康且锁定蓝4，U121、真实J3约642 mm、cfg1、红49/蓝28，保持零速。该零速校色预检证明可进入下一轮观察，不证明车体实际搜索、纠偏或停靠；随后画外蓝4实体POWER试验进入短暂APPROACH后失锁重搜，最终NOT_FOUND/SCAN_BUDGET，未停靠，详情单列。上述运行日志位于`build/remaining_20261104/`，不自动成为仓库内完整日志包。

**English**

`build/member_b/20261104T175030_045504Z_build/result.json` finished **PASS**: Full Compilation **1260.493 seconds**, separate post-fit gate **25.832 seconds**, with 0 errors, 92 warnings and 0 critical warnings. All 63 build-source files matched the frozen working source. Utilization is **29249/32070 ALMs (91%)**, 40840 registers, 357/397 M10Ks, 2802640 memory bits, 51/87 DSPs and 2/6 PLLs. Across four corners and 16 setup/hold/recovery/removal checks, worst margins are **+0.909/+0.118/+26.947/+0.401 ns** respectively. The 88-check report gate passed with all illegal and unconstrained counts at zero. Synchronizer coverage is 63/63 at each corner; MTBF remains unassessed. writeGray/readGray/timeGray cover 9/9/32 bits; resultToCamera1588, requestCdc22 and resultToDisplay979 physical endpoints have complete expected coverage. Worst max-skew/net-delay constraint margins are 18.498/13.844 ns, not measured propagation delays.

Build completion was **2026-11-04 18:11:56.936771 UTC**. The original SOF is `source/quartus/output_files/PartBDebug.sof` under that build directory, **6706157 bytes**. `build/remaining_20261104/program_e10_console.log` records actual programming and E7070010 identity readback **PASS**, finishing at **18:12:33.831751 UTC** (05:12:33.831751 AEDT the following day). This is E10's own build/programming result, not an inherited E9 artifact or timing claim.

After programming, VISION_ONLY/disarmed/zero was established and the applicable same-floor 13.6-second scan budget explicitly restored. All 4 independent C/B samples in `e10_blue4_calibration_preflight.json` were healthy and locked on blue4 at U121, real J3 approximately 642 mm, cfg1 and red49/blue28, while remaining at zero speed. This stationary calibration preflight permits the next observation but does not establish physical searching, steering or docking; the subsequent physical POWER trial briefly entered APPROACH, then lost the target and resumed search, ending NOT_FOUND/SCAN_BUDGET without docking as recorded separately. Runtime logs are under `build/remaining_20261104/` and are not automatically a complete committed log bundle.

### E10蓝4画外实机：短暂进入接近后失锁，搜索预算耗尽 / E10 out-of-view blue4 hardware trial: brief approach, lost target, exhausted search budget

**中文**

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

**English**

`build/remaining_20261104/integrated_blue4_e10_search_01.jsonl` and `e10_operator_notes.json` record the real camera and real J3/IR/UART on the same plastic floor and chassis supply. Physical POWER started the task; host START, synthetic writes and host heartbeats were all zero. The run contains **370 CCTL and 43 BCTL snapshots**, with an observer-recorded task duration of **22.2096082 seconds** and result **NOT_FOUND_OBSERVED / SCAN_BUDGET**, not DOCKED or successful search-to-dock.

| Host observation time (seconds) | Recorded behaviour |
|---|---|
| 24.5707036 | First ARM and normal SEARCH at +4/−4 |
| 26.292697 | Target discovery led to stopped ACQUIRE confirmation, followed by a lock at centred U121 |
| 27.843132 | Brief APPROACH requested +5/+5, exercising E10's direct forward-entry path |
| 27.952800 | Target loss entered LOST and cancelled forward motion |
| 28.253924 | Normal-direction SEARCH resumed approximately 300 ms later |
| From 29.909043 | Later observations reached U179/201 near the edge and ALIGN, then lost the marker again; opposite-wheel requests here were ALIGN, not reverse SEARCH recovery |
| 46.7802808 | The 13.6-second accumulated scan budget was exhausted: NOT_FOUND, disarmed and zero transmission complete; final J3 was 450 mm |

All task C samples had healthy sources, and all 43 B frames were good/fresh. B processing latency was **38.818–48.436 ms**, with no observed transport or candidate fault in this run. There was no DOCKED and no reverse SEARCH, so the bounded recovery introduced in E9 still lacks physical activation evidence. Final J3 450 mm is a terminal range reading, not an accepted docking distance or ruler-based accuracy measurement. Polled states do not measure the duration or displacement of the brief forward motion. Healthy frames/sources do not exclude a temporary target-identity or geometry loss.

The user reported: “搜到后停止了，此时蓝四在正中。随后又重新开始搜索，再一次掠过蓝四后停止” — it stopped after finding blue4 almost centrally, then resumed searching and passed it again before stopping. Follow-up confirmed brief forward travel before turning away, a fixed paper target throughout and both wheels stopped at the end. Cleanup returned VISION_ONLY, disarmed, L/R zero and zeroSent=true, with `cleanupErrors=[]`. E10 therefore demonstrated entry into forward motion with the wider band, but **resumed searching after target loss still caused the target to be passed again; the out-of-view search-to-dock requirement has not passed**. This release preserves that failure; later repairs require separate verification.

### E11：失锁后完整停车重确认与调参接口验证 / E11: complete stationary recovery after loss and tuning-interface validation

**中文**

E10曾在U121短暂进入APPROACH，随后LOST约300 ms即回SEARCH，固定目标再次掠过且未停靠。E11将LOST等待结束后的出口统一改为ACQUIRE，无论此时是否为健康NOT_FOUND，都先完成零速UART、1.5秒驻留、新采集边界及三帧确认，再决定接近、对准或继续搜索。`stationaryRecoveryRequired`保留该停车确认义务，跨HOLD和来源中断仍有效，包括丢牌与HOLD同一周期发生；一旦该义务已建立，就不能因安全恢复或暂时无目标跳过确认。普通跟踪失锁不新授予E9反向回扫资格，同一搜索预算、已用回扫次数及120秒任务计时不重置。这是针对真实失败的修正实现，已通过独立控制验证并下载；后续实机已采到预算未耗尽时的LOST→ACQUIRE，但抽动与过冲仍在，未完成画外搜索停靠。

该新义务仅在ALIGN/APPROACH失效时建立，包括失效与HOLD同周期发生。若目标仍有效时先进入HOLD，随后才在HOLD内丢牌，则沿用旧分支：障碍和来源条件恢复后，健康NOT_FOUND仍可能直接回SEARCH。这个先HOLD、后丢牌的顺序没有纳入本轮修复，保留为已知边界，不称全部HOLD恢复都已强制停车确认。

调参端点独立聚焦记录为`build/remaining_20261104/tuning_e11_20261104T182254Z/result.json`：ModelSim **128检查/20报告PASS，1.5052586秒，0错误/0警告**。主机测试`build/remaining_20261104/tuning_e11_host_tests.log`为 **18测试PASS，0.155秒**；实际生产Tcl脚本配mock传输测试`tuning_e11_tcl_tests.log`为 **2测试PASS，0.938秒**。Tcl结果验证脚本协议检查及设计族识别，没有使用实物USB-Blaster，不是实机调参或JTAG运动验证。

E7070011冻结源码已通过独立主控制定向、正式R6最终轮、Full Compilation/post-fit与实际下载，停车调参也已获得真实JTAG读回证据；地面首轮及search3搜索均NOT_FOUND，三个短时对照均INCOMPLETE；发布保留全部失败，未完成画外搜索停靠。保持用户取消蓝5/6单独地面测试的范围，不用旧版停靠成功覆盖E11的新行为。

**English**

E10 briefly entered APPROACH at U121, then resumed SEARCH approximately 300 ms after LOST, passing the fixed target again without docking. E11 sends every completed LOST wait to ACQUIRE, including healthy NOT_FOUND input. A complete zero-speed UART message, 1.5-second dwell, a fresh capture fence and three-frame confirmation precede the next approach, alignment or search decision. `stationaryRecoveryRequired` retains this obligation across HOLD and source interruption, including simultaneous target loss and HOLD. Once established, this obligation cannot be bypassed by safety recovery or an absent target. Ordinary tracking loss does not grant new E9 reverse-recovery permission, replenish used reverse steps or reset the scan budget/120-second task timer. This implementation has passed independent control verification and been programmed; its physical effect still requires the new trial, without claiming resolved overshoot or closed-loop completion.

The new obligation is established only when ALIGN/APPROACH becomes invalid, including invalidation and HOLD in the same cycle. If HOLD begins while the target is still valid and the target is lost only afterwards within HOLD, the existing branch remains: once obstacle/source conditions recover, healthy NOT_FOUND may return directly to SEARCH. This HOLD-before-loss sequence is outside this repair and remains a known boundary; not every HOLD recovery is forced through stationary confirmation.

Independent tuning-endpoint evidence is `build/remaining_20261104/tuning_e11_20261104T182254Z/result.json`: ModelSim **128 checks/20 reports PASS in 1.5052586 seconds, 0 errors/0 warnings**. Host tests in `build/remaining_20261104/tuning_e11_host_tests.log` passed **18 tests in 0.155 seconds**. Tests of the actual production Tcl script with a mock transport in `tuning_e11_tcl_tests.log` passed **2 tests in 0.938 seconds**. The Tcl result checks script protocol validation and design-family identification without a physical USB-Blaster; it is not hardware tuning or JTAG motion evidence.

Frozen E7070011 source has passed independent main control checks, the final formal R6 run, Full Compilation/post-fit and actual programming. Stationary tuning has real JTAG readback evidence; the original/search3 ground searches ended NOT_FOUND and all three short comparisons remained INCOMPLETE; this release preserves those failures without search-to-dock acceptance. The user's cancellation of individual blue5/6 ground trials is retained; earlier docking results do not establish E11 behaviour.

### E11独立控制验证、R6失败与调度修正 / E11 independent control checks, failed R6 and scheduling repair

**中文**

控制定向最终记录`build/remaining_20261104/control_e11_20261104T182830Z/result.json`为 **PASS，34.258085秒**，一次ModelSim编译、三个配置，0错误/0警告。runtime开启的生产负sign和泛型正sign各 **996检查/358条完整UART**，其中runtime专属28条；runtime关闭、旧110–130严格参数且tuning输入为X的兼容配置 **847检查/289 UART**。覆盖持续NOT_FOUND下LOST仍必须ACQUIRE、失锁与HOLD同周期、来源中断后重新驻留、确认超时才恢复SEARCH、STOP取消，以及五项调参边界、75–165前进范围、fine+1差速和非法参数零运动门控。配置检查数不相加冒充独立功能数。

前置`control_e11_20261104T182549Z`因TB末尾打印参数不足失败，`182629Z`及diagnostic因期望串中`%s`空正号多产生空格失败；实际UART内容正确，修正只涉及TB格式，不是生产RTL功能失败。原失败日志保留，不能写成“没有失败尝试”；最终通过来自上述单独完整运行。

第一次正式R6 `build/member_b/20261104T182917_566351Z_verilator_course/result.json`为 **FAIL，302.015209秒、退出1、targetMet=false**。13个正常场景均PASS，但最后故意坏锁定mutant的编译达到300秒总期限，未得到CAUGHT，不能将此轮标为完整通过。随后仅优化`tools/lib/verilator_suite.py`调度：首对长仿真运行期间，主线程按顺序预编译后续场景；始终最多两个仿真、一个编译进程、jobs4及原300秒总期限。保留本次fresh源码/精确输入哈希缓存，已准备二进制使用前再次核对字节；未删场景、帧数或断言，也不复用往轮二进制。

runner最终 **18项HOST_RUNNER测试PASS，1.962秒**，日志`r6_e11_overlap_host_tests_final.log`；最初sandbox临时目录WinError5及先前native通过日志保留，不混为RTL失败。全新第二轮`build/member_b/20261104T184126_548104Z_verilator_course/result.json`独立 **PASS，219.199994秒、退出0、13 PASS＋mutation CAUGHT、cleanBuild=true、targetMet=true**，61个新源文件、11个场景预编译，仍单编译/最多2模拟。此实测满足285秒目标，首轮失败未覆盖；生产RTL冻结不因runner调度修改而改变。

**English**

Final control evidence `build/remaining_20261104/control_e11_20261104T182830Z/result.json` is **PASS in 34.258085 seconds**, with one ModelSim compilation, three configurations and 0 errors/0 warnings. Runtime-enabled production negative and generic positive TURN_SIGN each passed **996 checks/358 complete UART messages**, including 28 runtime-specific messages. Runtime-disabled compatibility with legacy U110–130 and an X tuning input passed **847 checks/289 UART messages**. Coverage includes LOST-to-ACQUIRE despite continuous NOT_FOUND, simultaneous loss/HOLD, renewed dwell after source interruption, SEARCH only after confirmation timeout, STOP cancellation, tuning boundaries, the U75–165 approach corridor, fine+1 differential steering and zero output for invalid parameters. Parameter-case counts are not additive independent feature counts.

Earlier `control_e11_20261104T182549Z` failed because the bench's final display omitted an argument; `182629Z` and diagnostic attempts failed because an empty positive-sign `%s` inserted an extra expected space. Actual UART content was correct; repairs concerned bench formatting, not production RTL. Original failure logs remain, so this is not described as having no failed attempt. The final pass comes from the separate complete run above.

The first formal R6, `build/member_b/20261104T182917_566351Z_verilator_course/result.json`, **failed in 302.015209 seconds, exit1, targetMet=false**. All 13 normal scenarios passed, but the final intentionally broken-lock mutant compilation reached the 300-second overall deadline; CAUGHT was not obtained. The subsequent change only optimized scheduling in `tools/lib/verilator_suite.py`: during the initial two long simulations, the main thread serially precompiles later scenarios, retaining at most two simulations, one compiler process, jobs4 and the original 300-second deadline. Fresh sources and exact current-invocation input hashes remain, with prepared binary bytes rechecked before use. No scenario, frame or assertion was removed, and older-run binaries were not reused.

The runner's final **18 HOST_RUNNER tests passed in 1.962 seconds**, logged in `r6_e11_overlap_host_tests_final.log`; initial sandbox temporary-directory WinError5 and an earlier native pass log remain separate from RTL results. A fresh second R6 at `build/member_b/20261104T184126_548104Z_verilator_course/result.json` independently **passed in 219.199994 seconds, exit0, 13 PASS plus mutation CAUGHT, cleanBuild=true and targetMet=true**, using 61 fresh source files and 11 prefetched scenarios with the same single-compiler/two-simulation limits. This measured result meets 285 seconds without overwriting the initial failure. Scheduling changes did not modify the frozen production RTL.

### E11完整构建、实际下载与停车调参实测 / E11 complete build, programming and physical stationary tuning

**中文**

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

**English**

`build/member_b/20261104T182211_444905Z_build/result.json` finished **PASS**: Full Compilation **1375.853 seconds**, post-fit gate **26.278 seconds**, 0 errors, 92 warnings and 0 critical warnings. Utilization is **29403/32070 ALMs (92%)**, 41147 registers, 357/397 M10Ks, 2802640 memory bits, 51/87 DSPs and 2/6 PLLs. Worst four-corner setup/hold/recovery/removal margins are **+0.237/+0.120/+26.616/+0.471 ns**. The 88-check report gate passed with zero illegal/unconstrained items; synchronizer coverage is 63/63 at each corner, with MTBF unassessed. Write/read/time Gray coverage is 9/9/32 bits; resultToCamera1589, requestCdc22 and resultToDisplay979 physical endpoints have complete coverage. Worst max-skew/net-delay constraint margins are 18.670/12.457 ns, not measured propagation times.

Build completion was **2026-11-04 18:45:34.129044 UTC**; the original SOF is `source/quartus/output_files/PartBDebug.sof` under that build directory, **6706153 bytes**. `program_e11_console.log` records actual programming and E7070011 identity readback **PASS**, completing at **18:46:11.345908 UTC** (05:46:11.345908 AEDT next day). These results do not inherit E10 timing/artifacts or rewrite earlier failures.

`build/remaining_20261104/e11_tuning_hardware.json` records **physical JTAG stationary tuning PASS**, distinct from mocked transport. Every step remained VISION_ONLY, disarmed, without motion permit, with both commands zero and zeroSent=true; START/synthetic writes/heartbeats were all zero:

| Physical operation | Independent readback and scope |
|---|---|
| Initial defaults | search/turn/approach/fine/tolerance = 4/4/5/3/30, with readable A1 capability |
| Restore verified search4 baseline | Existing same-plastic-floor three-circle 13.6-second basis, scanCalibrated=true |
| Write turn3, approach6, fine4, tolerance35 | 4/3/6/4/35, matching a separate independent readback; unchanged search retains calibration |
| Write search3 | 3/3/6/4/35, scanCalibrated=false; no movement or revolution measurement at 3 cm/s |
| Restore defaults | 4/4/5/3/30, with scanCalibrated still false; defaults do not automatically restore qualification |
| Restore the original search4 record and clean up | Explicit restoration of the applicable existing 13.6-second record, then STOP/disarmed/zero; not calibration for search3 |

This verifies parameter writing, retention, readback, capability and calibration invalidation. It does not measure wheel speeds, stability or docking at changed speeds. All 4 independent C/B pairs in `e11_blue4_calibration_preflight.json` were healthy and locked on blue4 at U116/J3 approximately 660 mm, cfg1 calibrated, all tuning defaults and scanCalibrated=true, while stationary. The subsequent out-of-view and short-comparison failures are recorded separately; runtime files are under `build/remaining_20261104/`.

### E11同一固件的地面试验与会话调参 / E11 ground trials and session tuning with the same firmware

**中文**

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

**English**

The user requested no new firmware revision. These trials retain the same **E7070011** production RTL and successfully built SOF, changing only session settings through stopped `tune` and `scan` commands. No new RTL repair or compilation replaces the earlier failures. Reset defaults remain **search/turn/approach/fine/tolerance = 4/4/5/3/30**. The latest experimental setting is **3/5/4/3/40**, with search3, turn5, approach4, fine3 and ±40 tolerance (U80–160), plus a **15.1-second** scan budget. These volatile settings do not survive KEY0, power loss or reprogramming. The turn5 comparison, then using approach5, showed motion but remained INCOMPLETE with overshoot; the approach4 comparison also ended INCOMPLETE, with twitching/overshoot unresolved; this round concludes without further tests.

**The first ground search did not pass.** `integrated_blue4_e11_search_01.jsonl` records 368 CCTL/50 BCTL snapshots, physical POWER and zero host START/synthetic writes/heartbeats. Observer task duration was **28.0071143 seconds**, ending **NOT_FOUND/SCAN_BUDGET**, followed by VISION_ONLY/disarmed/zeroSent cleanup and J3 398 mm. C polling directly sampled reverse SEARCH (−4,+4) twice. A further 149999 µs scan-counter increment is consistent with a third short step, but is an inference rather than a complete third-step waveform or mechanical reverse measurement. The user saw continued anticlockwise motion after stopping and did not observe a reverse correction. Reverse commands therefore do not establish effective mechanical recovery. There was no ALIGN, APPROACH or LOST in this run, so the LOST repair was not exercised physically in it.

All 50 B frames were fresh/good, at cfg1/red45/blue24, different from E10's configuration. Sampled candidates were near the edge or rejected for orientation, with no accepted targetU captured by B polling. C's second brief observed/locked interval need not appear in sparse B polls; this neither proves no recognition nor continuous locking or a throughput bottleneck. The user restored the vehicle position after stopping, so subsequent scenes retain their own scope.

**search3 circle timing and the 15.1-second basis.** Changing search4→3 cleared scanCalibrated. Ground timing used CHASSIS_INJECT synthetic healthy/no-target reports through the real controller/J3/IR/UART, with the user pressing A to stop. These are physical turning observations, not camera-based marker-search tasks. Times below are FPGA accumulated permitted SEARCH requests at the IR stop, not yaw feedback or independent mechanical-settling measurements; operator reaction remains part of the observation:

| Original record under build/remaining_20261104 | Accumulated SEARCH time | Physical report and scope |
|---|---|---|
| `ground_e11_search3_circle1.jsonl` | **30.014554 seconds** | Two complete revolutions plus approximately 10°, with about 3 cm backward drift. Not one revolution; division by two gives 15.007277 seconds only as a per-revolution average reference |
| `ground_e11_search3_circle2.jsonl` | No valid turning time | IR remained latched, two status samples and no motion: **TRIAL_INVALID**, retained and excluded from valid circle counts |
| `ground_e11_search3_circle2_retry.jsonl` | **14.093147 seconds** | One revolution plus approximately 7.5°, with the right wheel travelling about 1 cm more |
| `ground_e11_search3_circle3.jsonl` | **14.691960 seconds** | One revolution plus approximately 3°, with about 4 cm backward drift |

A conservative 15.1-second bounded budget was written from **two single-revolution observations and one double-revolution reference**, recorded in `e11_search3_scan_15100ms.json`. This is not three precise single circles, exact 360° calibration or measured autonomous stopping-angle error. The former 13.6 seconds belongs to search4 and cannot be applied to search3; the current 15.1 seconds must not be blindly retained after reset restores search4. Reverse recovery consumes the same total budget, so net forward swept angle is not accumulated command time. The laboratory epoxy floor remains untested.

**Slow search still did not dock.** `integrated_blue4_e11_search3_02.jsonl` records **593 C/69 B snapshots, 43.5151717 seconds of task observation and NOT_FOUND/SCAN_BUDGET**, with physical POWER, no host START/synthetic/heartbeat and empty cleanupErrors. The user described missing the marker on the first circle, discovering it on the second, then a correction where only the right wheel moved and overshot. “First/second circle” is preserved as operator description, not converted into measured yaw or two timed complete circles. The log observed three LOST→ACQUIRE→ALIGN segments, all after scan-budget exhaustion; the old budgetDone branch could do the same, so this trial alone does not establish the new LOST repair or resolved overshoot/docking. Sparse snapshots do not reconstruct unmeasured wheel speed or pulse duration.

**Low-turn-speed isolation did not align.** `integrated_blue4_e11_turn3_15s.jsonl` used search3, turn3, approach5, fine3, tolerance40, retaining **273 C/35 B snapshots**. The 15-second observation limit produced taskObservationSeconds **15.1179462**, ending **INCOMPLETE**, followed by host STOP/zero cleanup with no errors. Blue4 remained near U40→41; the user saw only twitching, without effective alignment. The subsequent turn5 comparison used the same firmware at **3/5/5/3/40**, with its actual outcome recorded separately. Successful parameter writes do not establish mechanical effectiveness.

### E11 turn5同场景对照：能够转动，但仍过冲 / E11 same-scene turn5 comparison: motion but continued overshoot

**中文**

`integrated_blue4_e11_turn5_15s.jsonl`在同一固件、search3/turn5/approach5/fine3/tolerance40下完成 **340 C/44 B**、taskObservationSeconds **15.002259秒**，结果 **INCOMPLETE**。结束由15秒主机观察期限收尾，cleanupErrors为空，最终VISION_ONLY、未ARM、左右0、zeroSent、J3596 mm；没有完成搜索停靠，也不是生产120秒任务限到期。

目标U由41→44→50→53→82；主机37.748570–38.379696秒采到APPROACH +5/+5，38.501820秒为LOST/0/0，38.813秒进入ACQUIRE，40.472秒为ALIGN −5/+5。B在38.983秒已采到U195，随后197/198，目标再次到右边缘。**整个观察中scanRemaining均为15100000 μs**，所以本轮在扫描预算未耗尽时实际出现LOST→ACQUIRE，而非直接回SEARCH，是E11新增恢复路径的板上证据；该状态顺序不证明车身已机械停稳，也没有消除越过中心或失锁。

用户原话：“**最开始右轮短抽，然后动了一下几乎回正，然后又在右偏（两侧轮子都有动作），然后4到了右侧边缘，随后左轮抽动，或是因为超时而停止。整体是由前进一些距离的**”。较turn3只有抽动，本轮用户确实看到双轮动作与一段前进，但对准/接近仍未完成；不能把这一观察写成轮速匹配、稳定对准或成功停靠。

此前`search3_02`的三段LOST→ACQUIRE→ALIGN均发生在扫描预算耗尽后，旧budgetDone路径也会进入ACQUIRE，**不能单独用那轮证明本次LOST修复**；本轮未耗尽预算的序列提供了不同范围的证据。

接着只通过停车调参将approach5降至4，最新会话参数为 **3/5/4/3/40**，15.1秒预算保留；默认仍4/4/5/3/30、生产RTL及E7070011不变。随后的15秒对照也已INCOMPLETE，详情见下一节；减速未解决本轮过冲。

**English**

`integrated_blue4_e11_turn5_15s.jsonl` used the same firmware at search3/turn5/approach5/fine3/tolerance40, retaining **340 C/44 B snapshots** and taskObservationSeconds **15.002259**, ending **INCOMPLETE**. The 15-second host observation limit ended the run; cleanupErrors was empty and final state was VISION_ONLY, disarmed, L/R zero, zeroSent and J3 596 mm. Search-to-dock did not complete; the production 120-second task limit was not reached.

Target U progressed 41→44→50→53→82. APPROACH +5/+5 was sampled at host 37.748570–38.379696 seconds, LOST/0/0 at 38.501820, ACQUIRE at 38.813 and ALIGN −5/+5 at 40.472. B already sampled U195 at 38.983, followed by 197/198 near the right edge. **scanRemaining stayed 15100000 µs throughout**, so LOST→ACQUIRE actually occurred with scan budget unexhausted rather than immediately returning to SEARCH. This is board-state evidence of E11's revised recovery route, not proof of mechanical standstill or resolved centre-crossing/target loss.

The user reported an initial right-wheel twitch, a movement that almost recentered the vehicle, then rightward drift with both wheels moving, the marker reaching the right edge, a later left-wheel twitch and some forward travel before stopping or the timeout. Compared with turn3's twitching, both-wheel action and forward travel were physically observed, but alignment/approach still did not complete. This does not establish matched wheel speeds, stable alignment or docking.

In the earlier `search3_02` trial, all three LOST→ACQUIRE→ALIGN segments occurred after budget exhaustion. The old budgetDone branch could also enter ACQUIRE, so **that trial alone does not establish the new LOST repair**. The present unexhausted-budget sequence provides a different scope of evidence.

Only approach was then reduced from 5 to 4 through stationary tuning. The latest session setting is **3/5/4/3/40**, retaining 15.1 seconds; defaults remain 4/4/5/3/30 and production RTL/E7070011 are unchanged. The subsequent 15-second comparison also ended INCOMPLETE, as recorded next; lower speed did not resolve this overshoot.

### E11最后一轮approach4：减速未消除抽动和过冲，停止追加测试 / Final E11 approach4 trial: lower speed did not remove twitching/overshoot; testing concluded

**中文**

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

**English**

`integrated_blue4_e11_turn5_approach4_15s.jsonl` used the same E7070011 at **search3/turn5/approach4/fine3/tolerance40**, retaining **289 CCTL and 36 BCTL snapshots**, physical POWER and zero host START/synthetic writes/heartbeats. Under the 15-second host observation limit, taskObservationSeconds was **15.0186774**, ending **INCOMPLETE**. cleanupErrors was empty; final state was VISION_ONLY, disarmed, L/R zero, zeroSent=true and J3 619 mm. No DOCKED occurred. Observation-limit cleanup is neither autonomous docking nor expiry of the production 120-second task limit.

Blue4 remained at U41 for several sampled cycles, then moved 43→46→49→126→140 before becoming NOT_FOUND. APPROACH +4/+4 was sampled at host 36.730 seconds and ACQUIRE at 37.366. The user reported: “最开始两轮一起往前抽动，随后右轮抽了波大的，让蓝四几乎居中，然后又抽了波大的，导致蓝四有些超出右边缘” — both wheels initially twitched forward, then a larger right-wheel movement nearly centred blue4, followed by another large movement that took it beyond the right edge. Lowering the forward request did not resolve uneven short-pivot startup, twitching or overshoot in this run. Coordinate changes do not measure wheel speed, displacement or exact angle.

| E11 real-camera ground trial | Task observation duration | Actual outcome |
|---|---:|---|
| Original search4/default search |28.0071143 s | NOT_FOUND/SCAN_BUDGET; reverse SEARCH commands sampled, without confirmed mechanical recovery |
| search3 with 15.1-second search budget |43.5151717 s | NOT_FOUND/SCAN_BUDGET; post-budget LOST→ACQUIRE alone does not establish the new repair |
| turn3/approach5/tolerance40 isolation |15.1179462 s | INCOMPLETE, twitching without effective alignment |
| turn5/approach5/tolerance40 isolation |15.002259 s | INCOMPLETE; LOST→ACQUIRE observed with budget remaining, but overshoot and target loss persisted |
| turn5/approach4/tolerance40 isolation |15.0186774 s | INCOMPLETE; lower forward speed still twitched and overshot |

This round concludes without further trials, RTL changes, compilation or a new firmware version. Final state is E7070011, VISION_ONLY, disarmed and zero-speed. The volatile **3/5/4/3/40 and 15.1-second** session settings remain as **an experiment, not a validated recommended configuration**. Firmware defaults remain **4/4/5/3/30**; KEY0, power loss or reprogramming restores them and loses runtime scan calibration. Stationary tuning/calibration invalidation passed physically, and the revised LOST route has board evidence under the stated conditions. Mechanical overshoot, sustained acquisition and out-of-view search-to-dock remain unverified/unsuccessful. Historical E8 docking from visible blue1/3/4 targets does not establish this version's complete-task acceptance.

### E12独立控制回归与保留的失败尝试 / E12 independent control regression and retained failed attempt

**中文**

首次控制定向目录`build/remaining_20261104/control_e12_20261104T192836_046724Z/`保留为失败尝试：runtime分支调整后，TB仍引用旧层次名；生产源码未因此改变，修复只涉及TB引用。随后一次编译、三配置完整运行`build/remaining_20261104/control_e12_20261104T192902_661125Z/result.json`独立**PASS，44.0894113秒、0 errors/0 warnings**：runtime两种TURN_SIGN各**2041检查/500完整UART**；关闭runtime且timing输入未知的legacy参数配置**848检查/289 UART**。原失败不覆盖，逻辑计时及完整UART检查不等于真实电机速度阶段或机械停稳验证。正式R6结果见下文；完整构建/post-fit、下载与实机结果继续分别记录。

**English**

The first focused attempt in `build/remaining_20261104/control_e12_20261104T192836_046724Z/` remains a failure: the bench referenced an old hierarchy after the runtime branch changed. Production source was unchanged; only the bench reference was corrected. A subsequent single compilation and three complete configurations in `build/remaining_20261104/control_e12_20261104T192902_661125Z/result.json` independently **passed in 44.0894113 seconds with 0 errors/0 warnings**. Runtime-enabled positive and negative TURN_SIGN each passed **2041 checks/500 complete UART messages**; the runtime-disabled legacy configuration with unknown timing input passed **848 checks/289 messages**. The original failure is retained. Logical timers and complete UART checks do not establish physical speed stages or mechanical settling. Formal R6 evidence follows below; Full Compilation/post-fit, programming and physical evidence remain separate.

### E12正式R6首次完整运行通过 / E12 first complete formal R6 passed

**中文**

`build/member_b/20261104T193009_881634Z_verilator_course/result.json`独立**PASS，223.404755秒、exit0、targetMet=true，13项PASS及mutation CAUGHT**。本版首次正式R6即达到285秒目标；61个fresh源文件，jobs4、最多2个仿真与1个编译进程，11项预编译，继续沿用E11经验证的当前调用精确输入/产物检查及调度策略。没有减少场景、输入帧数或断言，也没有借旧版结果填补本版证据。此前E11的302.015209秒FAIL仍是历史失败，未被这次E12成功覆盖。

此前综合于悉尼时间2026-11-05 06:32:15完成、DSP51；随后完整构建/post-fit、下载及静止验收也已取得下述独立PASS。R6通过本身不证明实物起步同步或搜索停靠成功。

**English**

`build/member_b/20261104T193009_881634Z_verilator_course/result.json` independently **passed in 223.404755 seconds, exit0, targetMet=true, with 13 PASS plus mutation CAUGHT**. E12's first formal R6 meets the 285-second target. It used 61 fresh source files, jobs4, at most two simulations and one compiler process, and 11 prefetched scenarios, retaining E11's verified current-invocation input/artifact checks and scheduling policy. No scenario, input frame or assertion was removed, and no previous-version result substitutes for this run. E11's earlier 302.015209-second failure remains historical evidence.

Synthesis finished at 06:32:15 Sydney time on 2026-11-05 with 51 DSPs; the subsequent complete build/post-fit, programming and stationary checks have independently passed as recorded below. Passing R6 alone does not establish synchronized physical startup or completed search-to-dock.

### E12完整构建、实际下载与停车pulse参数验证 / E12 complete build, programming and stationary pulse verification

**中文**

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

**English**

`build/member_b/20261104T192605_706632Z_build/result.json` is **PASS**: Full Compilation **1163.903 seconds**, post-fit gate **26.783 seconds**, 0 errors, 92 warnings and 0 critical warnings. Final utilization is **29647/32070 ALMs (92%)**, 41286 registers, 357/397 M10Ks, 2802640 memory bits, 51/87 DSPs and 2/6 PLLs. The four-corner 16-check minimum setup/hold/recovery/removal margins are **+0.842/+0.102/+28.060/+0.434 ns**. All 88 report-gate checks passed with zero illegal/unconstrained items; synchronizer coverage is 63/63 per corner, while MTBF remains NOT_ASSESSED. Gray coverage is 9/9/32; resultToCamera1589, requestCdc22 and resultToDisplay979 have complete corresponding physical coverage. Minimum max-skew/net-delay constraint margins are 18.127/14.470 ns, not propagation-delay measurements.

Build completion was **2026-11-04 19:45:56.942735 UTC**. The original `source/quartus/output_files/PartBDebug.sof` is **6706156 bytes**. `e12_production_source_match.json` records all 63 production files byte-matching this build's copies. `program_e12_console.log` records actual programming and **E7070012 identity readback PASS**, finishing at **19:46:26.577567 UTC (06:46:26.577567 Sydney time next day)**. These are independent E12 results rather than inherited E11 artifacts or timing.

`build/remaining_20261104/e12_pulse_hardware.json` records **physical JTAG stationary parameter PASS**. All five samples and final cleanup remained VISION_ONLY, disarmed, without motion permit, both commands zero and zeroSent=true. START, synthetic writes and heartbeat counts were all zero; cleanupErrors was empty.

| Stationary operation | Independent state and scope |
|---|---|
| Read defaults | Pulse min/max/kickMs/kickSpeed20/100/0/5, with tune still 4/4/5/3/30 |
| Write initial two-stage configuration | Pulse100/200/60/5: total 100–200 ms and initial 60 ms at a 5 cm/s request |
| Read independently again | All four values match; five-field tuning and scan status remain unchanged |
| Write range-edge values | Pulse300/300/100/8, written/read only in stopped V1; **no movement at that speed** |
| Restore defaults and clean up | Pulse20/100/0/5, tuning still default and scan still uncalibrated; stopped/zeroSent confirmed |

This establishes real transport, atomic retention, readback and field independence. It does not establish corresponding wheel speed, startup force or mechanical stages. Four independent healthy C/B lock samples in `e12_blue4_calibration_preflight.json` showed U113, J3 approximately 655–659 mm and calibrated cfg1, all while stationary.

`e12_first_profile_config.json` then wrote the first experimental **tune search3/turn3/approach5/fine3/tolerance40** and **pulse min100/max200/kickMs60/kickSpeed5** while stopped, restoring the existing same-plastic-floor search3 15.1-second scan record. Final state was scanCalibrated=true, V1/disarmed/zero. That basis still consists of E11's two single circles plus one double-circle reference; rewriting it is not precise 360° calibration. The first actual 15-second comparison is now complete but INCOMPLETE; the user reported slight improvement and continued rightward overshoot, as recorded below. Unequal startup, static friction or overshoot cannot be called resolved.

### E12首轮地面短转：用户反馈略好，仍偏右且未完成 / First E12 ground comparison: perceived improvement, but rightward overshoot and no completion

**中文**

`build/remaining_20261104/integrated_blue4_e12_kick5_cruise3_15s.jsonl`使用**tune3/3/5/3/40、pulse100/200/60/5、15.1秒扫描预算**，记录**320个CCTL和42个BCTL样本**。15秒观察窗实际taskObservationSeconds为**15.0223777秒**，终态**INCOMPLETE**，未DOCK；主机收尾后VISION_ONLY、未ARM、无permit、左右0、zeroSent=true、UART空闲、J3约659 mm，cleanupErrors为空。此观察窗结束不是产品120秒任务超时，也不是自动完成停靠。

用户原话：**“会好一点，但是转出来蓝色偏右一些”**。初始蓝4为U55、框左边界14且完整；BCTL采到U55→76→83→168→175。直接读到了ALIGN的`+3/−3`以及反向ALIGN的`−5/+5`命令，但没有在**同一次脉冲**内完整采到5→3转序，因此只能结合既有RTL逻辑验证与这些离散命令读数，不能宣称本轮完整机械两段过程已被采证。主要坐标偏移跨越APPROACH5/3→LOST停车，发生在反向ALIGN之前，不把整段目标位移都归因于反向短转。

任务采样中的来源一直健康，没有HOLD/IR/fatal；42个B样本均fresh/good。此范围内没有证据支持来源失效是本轮偏移的原因，但稀疏采样不能还原所有轮速、转角或机械停止时间。操作者主观“好一点”与末段仍偏右同时保留；本轮不算稳定对准或画外搜索停靠通过。

后续只将**fine3改为4**，其他保持，形成同一E12的第二轮实验**tune3/3/5/4/40**、pulse100/200/60/5及15.1秒扫描预算。此修改使远距差速慢轮变4，350–500 mm近距直行也变4、近距差速快轮为5；不是仅对一个动作单独改变速度。没有新增RTL、重新编译或新版本。第二轮结果及后续独立对照见下文，不用首轮反馈推定其效果。

**English**

`build/remaining_20261104/integrated_blue4_e12_kick5_cruise3_15s.jsonl` used **tune3/3/5/3/40, pulse100/200/60/5 and a 15.1-second scan budget**, retaining **320 CCTL and 42 BCTL samples**. The 15-second observation window produced taskObservationSeconds **15.0223777**, ending **INCOMPLETE** without DOCKED. Host cleanup left VISION_ONLY, disarmed, no permit, both commands zero, zeroSent=true, UART idle and J3 approximately 659 mm; cleanupErrors was empty. This is neither the production 120-second task deadline nor autonomous docking completion.

The user reported **“会好一点，但是转出来蓝色偏右一些”** (“a little better, but the blue marker ended somewhat to the right”). The complete initial blue4 box started at U55 with left edge 14; BCTL sampled U55→76→83→168→175. ALIGN requests of `+3/−3` and reverse-direction ALIGN of `−5/+5` were directly sampled, but **a complete 5→3 transition within the same pulse was not captured**. These separate command snapshots do not establish a fully observed physical two-stage sequence; the complete logical sequence has its separate RTL evidence. Most coordinate displacement crossed APPROACH5/3→LOST/zero before reverse ALIGN, so it is not all attributed to the later reverse pivot.

Task source samples remained healthy with no HOLD, IR or fatal state, and all 42 B samples were fresh/good. There is no source-health failure evidence explaining this displacement within the sampled scope, while sparse polls cannot reconstruct every wheel speed, angle or mechanical stopping time. The user's perceived improvement and continued rightward overshoot are both retained. Stable alignment and out-of-view search-to-dock did not pass.

Only **fine3→4** was then changed for the second same-E12 experiment: **tune3/3/5/4/40**, pulse100/200/60/5 and 15.1 seconds. This changes the far differential slow wheel to 4 and the 350–500 mm straight request to 4, with the near differential fast wheel now 5; it is not a change isolated to a single motion. There is no new RTL, compilation or firmware version. The second result and subsequent independent comparisons follow below, without inferring them from the first observation.

### E12第二至四轮：命令两段转序与有限回正证据 / E12 comparisons two to four: two-stage command sequences and bounded realignment

**中文**

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

**English**

All trials retain E7070012 and the original safety chain, changing only one parameter at a time while stopped in V1. No new RTL version or compilation was introduced. C/B counts are separate JTAG snapshots, not native camera-frame counts or mechanical speed samples.

| Trial / log | Change from previous trial | Samples and observation time | Actual outcome and cleanup |
|---|---|---|---|
| Second: `integrated_blue4_e12_fine4_15s.jsonl` | fine3→4; tune3/3/5/4/40, pulse100/200/60/5 | 422C/35B, 15.0445792 seconds | INCOMPLETE, empty cleanupErrors, final V1/zero/zeroSent and J3 approximately 636 mm |
| Third: `integrated_blue4_e12_kick6_reverse_15s.jsonl` | Only kickSpeed5→6 | 500C/39B, 15.0423456 seconds | INCOMPLETE, U187→181 and final J3 approximately 632 mm; alignment remained incomplete |
| Fourth: `integrated_blue4_e12_kick6_total 200_reverse_15s.jsonl` | Only minMs100→200, keeping maxMs200: fixed nominal 200 ms total, kick6/60 ms and turn3 afterward | 780C/60B, 3.8547528 seconds of task observation | ALIGN_CORRIDOR_OBSERVED; host STOP deliberately ended the diagnostic at the first sampled APPROACH5/5, final V1/zero/zeroSent, J3 approximately 591 mm and empty cleanupErrors; not DOCKED |

**The second trial captured two-stage board commands without independently validating fine4 differential correction.** Six complete same-ALIGN 5→3 magnitude sequences were directly sampled, three in each direction, all subsequently returning to zero. This is command-sequence evidence, not measured wheel speed, simultaneous startup or physical pulse duration. B positions were U49→71→153 after the third pivot and before APPROACH, then 159→178 and 188 after reverse alignment. Only 5/5 APPROACH was sampled, without 5/4. Therefore the first trial's hypothesis about forward differential steering causing the displacement was not supported here; neither a confirmed cause nor effective fine4 correction is established. The user reported that the initial right-wheel twitches visibly turned the vehicle a little, but a later large movement again put blue4 to the right.

**Raising the kick in the third trial still did not fully realign.** Starting near the same right-side U187, kick6 produced the user's observation that several brief left-wheel movements helped but did not finish alignment. B changed only U187→181 and the result stayed INCOMPLETE. This establishes limited observed motion, without proving a real 6 cm/s speed, overcome static friction or uniform step size.

**The longer total duration in the fourth trial brought the target into an acceptable region.** Two sequences of `−6/+6 → −3/+3 → 0/0` were directly sampled, with B at U181→171→104/105. All sampled source states were healthy, B was good/fresh, no HOLD/IR/fatal/transport fault occurred, and the 15.1-second scan budget was unused. The user reported: “几乎回正了，但是有点点偏左，不过勉强可以接受” — nearly aligned, slightly left, but acceptable. That acceptance is preserved without requiring further pursuit of exact centring in this diagnostic; uneven step sizes remain a limitation. The helper returned exit1 because the configured diagnostic stopped at the first APPROACH, not because the vehicle was uncontrolled or the log invalid. ALIGN_CORRIDOR_OBSERVED establishes entry into the approach corridor, not DOCKED or a completed search-to-dock task.

The subsequent, separate `e12_approach_after_alignment_preflight.json` recorded **3/3 healthy locks at U84 and J3 approximately 582 mm**. This is not the same sample as the prior U104/105 endpoint, and physical conditions cannot be assumed unchanged between them. The following `integrated_blue4_e12_approach_after_alignment.jsonl` uses **tune3/3/5/4/40, pulse200/200/60/6 and 15.1 seconds**, with at most 60 seconds to observe approach from an already visible target. Its actual INCOMPLETE result follows below; this is also not full search acceptance from outside the field of view.

### E12第五轮接近未完成：边缘丢牌、重新搜索与近障HOLD / Fifth E12 approach remained incomplete: edge loss, search and near-obstacle HOLD

**中文**

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

**English**

`build/remaining_20261104/integrated_blue4_e12_approach_after_alignment.jsonl` retained **tune3/3/5/4/40, pulse200/200/60/6 and a 15.1-second scan budget**, observing approach from an already visible target with **687C/85B samples**. taskObservationSeconds was **60.0399573**, ending **INCOMPLETE**. cleanupErrors was empty; final state was VISION_ONLY, disarmed, both commands zero, zeroSent=true, J3 approximately 254 mm and **sonarHold still true**. No DOCKED occurred; host cleanup is not autonomous docking.

Five short APPROACH segments were sampled, including one 5/4 request as well as 5/5 and 4/4, separated by repeated ALIGN. The user did not observe stable straight travel with small differential corrections, reporting: “一直左右校准方式前进，并没有直行然后小差速纠偏之类操作。然后在一次纠偏过了后360度重扫的时候，没有重新抓回蓝四” — it advanced through repeated left/right alignment, overshot during a correction and did not recover blue4 during the subsequent search. The user's “360-degree search” is retained as a description, not a measured full revolution without heading or independent angle measurements. Logs show edge rejection followed by two SEARCH segments that did not reacquire the target.

J3 triggered near-obstacle HOLD at **248 mm**, with a minimum sampled **240 mm**. The 48 HOLD samples ranged **240–254 mm**, below the required sequence of fresh safe readings at ≥300 mm; this run does not establish HOLD release. Protective near-obstacle stopping is not normal 350 mm docking, and 254 mm is neither a successful docking distance nor ruler-based accuracy.

All sampled source states were healthy, all 85 B samples were good/fresh and no transport fault was observed. Blue candidates reaching image edges 0/239 produced rejection codes 4/5. A final real capture, `capture20261104T200809_077960Z_capture`, passed freshness and CRC checks and showed the marker cropped at the image edge. **This is the final scene, not the first lost-target frame.** It is consistent with edge rejection without reconstructing the entire loss or proving every overshoot cause. Previously sampled 5→3 or 6→3 board-command sequences still do not measure wheel speed or perfectly matched startup.

| E12 ground observations retained in this release | Outcome | Evidence scope |
|---|---|---|
| Initial kick5/turn3 | INCOMPLETE15.0223777 seconds | User perceived slight improvement but rightward error; no complete same-pulse 5→3 sequence captured |
| Second fine4 | INCOMPLETE15.0445792 seconds | Six complete 5→3 command sequences; no 5/4 sampled, so no independent fine4 correction validation |
| Third kick6 | INCOMPLETE15.0423456 seconds | Brief left-wheel movements helped somewhat but did not fully align |
| Fourth total 200 ms | ALIGN_CORRIDOR_OBSERVED, 3.8547528 seconds | Two 6→3→zero command sequences; slight leftward error accepted; host STOP at first APPROACH, not DOCKED |
| Fifth already-visible-target approach | INCOMPLETE 60.0399573 seconds | Short approaches, repeated alignment, edge loss, unsuccessful search and final near-obstacle HOLD; docking did not pass |

This release record ends after those five trials. A subsequent same-version diagnostic changes only **tolerance40→30**, giving **tune3/3/5/4/30, pulse200/200/60/6**, still with 15.1 seconds. That initial five-trial release recorded it as pending. The sixth diagnostic below now provides user-confirmed continuous differential correction, without a complete docking pass or a generally validated recommendation. This tuning adds no RTL change, compilation or firmware version. SOF reset defaults remain **tune4/4/5/3/30 and pulse20/100/0/5**; KEY0, power loss or reprogramming does not retain experimental settings or scan calibration. Historical E8 visible-target docking and all failures retain their own version scopes and do not override the incomplete current main function.

### E12第六轮tolerance30：连续差速接近已观察，按诊断规则提前停车 / Sixth E12 tolerance30 diagnostic: continuous differential approach observed, then deliberate early stop

**中文**

本轮仍为**E7070012**，没有RTL变化、重新编译或新增R6；仅沿用停车时的**tune3/3/5/4/30、pulse200/200/60/6、扫描15.1秒**。`build/remaining_20261104/integrated_blue4_e12_tolerance30_approach15s.jsonl`保留**316C/28B**，taskObservationSeconds **2.2937077秒**，结果**APPROACH_INTERRUPTED**。本次诊断规则是在首次离开APPROACH时立即由主机STOP；因此该结果不是观察了自动恢复后宣告失败，也不是60 cm到DOCK的完整任务验收。

任务中连续采到**10个5/4、11个5/5、4个4/4**轮速请求状态样本，U由**77→87→113**。这些数字是重复状态快照数量，不是独立UART命令包数或实测轮速。用户确认：“**确实是不断修正，虽然最后有点偏右，但在可接受范围**”。结合其物理观察，本轮已经取得连续前进与差速修正的实机证据，区别于前五轮以反复原地对准为主的现象；但不据一次不同起始摆位的诊断认定容差是全部问题的唯一原因。

J3读数由约**625 mm下降到首次LOST时约440 mm**，清理后约**426 mm**。本轮没有ALIGN或SEARCH，最后已采B框完整；**恰好失锁对应的B帧未采到**，不能用最后完整框证明失锁帧也完整，亦不能将原因直接归为边缘裁切或传输故障。主机在此处终止，未继续观察E12的LOST→ACQUIRE恢复或后续DOCK过程。

随后独立`e12_after_tolerance30_preflight.json`的**3个样本均健康锁定，U141，J3分别414/414/409 mm**，保持VISION_ONLY、未ARM、零速。其位置与本轮末U113是不同采集时点，不能合并为同一帧或无变化的连续轨迹。后续从约41 cm位置的独立任务已取得DOCKED，详见第七轮；其两种距离读数差异仍保留。本轮与后续近距段即使都成功，也须保持分段证据，不能拼接成单次从60 cm自主到DOCK或从画外搜索到停靠的完整通过。

**English**

This remains **E7070012**, without RTL changes, recompilation or a new R6 run. The stopped configuration is **tune3/3/5/4/30, pulse200/200/60/6 and a 15.1-second scan budget**. `build/remaining_20261104/integrated_blue4_e12_tolerance30_approach15s.jsonl` retained **316C/28B snapshots**, with taskObservationSeconds **2.2937077** and outcome **APPROACH_INTERRUPTED**. The diagnostic deliberately sent host STOP on the first departure from APPROACH. It did not observe automatic recovery and then declare it failed, and it is not a complete 60 cm-to-DOCK acceptance run.

The task sampled consecutive groups of **10 requests at 5/4, 11 at 5/5 and 4 at 4/4**, while U progressed **77→87→113**. These counts are repeated state snapshots, not distinct UART packets or wheel-speed measurements. The user confirmed **“确实是不断修正，虽然最后有点偏右，但在可接受范围”** — continuous correction was visible and the remaining rightward offset was acceptable. Together with that physical observation, this provides real evidence of continuous advance with differential correction, unlike the repeated pivot-dominated earlier trials. A diagnostic with a different initial scene does not establish tolerance as the sole cause of all previous failures.

J3 changed from approximately **625 mm to 440 mm at the first LOST**, then approximately **426 mm after cleanup**. No ALIGN or SEARCH occurred. The last sampled B box was complete, but **the exact B frame corresponding to loss was not sampled**; the final complete box does not establish that the lost frame was complete or identify edge clipping/transport as its cause. The host ended this diagnostic there without observing E12's subsequent LOST→ACQUIRE recovery or DOCKED.

The separate `e12_after_tolerance30_preflight.json` then recorded **three healthy locks, U141 and J3 readings 414/414/409 mm**, while VISION_ONLY, disarmed and zero-speed. This differs from the prior U113 endpoint and cannot be merged into one frame or assumed unchanged continuous trajectory. The subsequent independent task from approximately 41 cm reached DOCKED, as recorded next, while its two distance readings remain discrepant. Even if both segments succeed, they must remain separate evidence rather than a fabricated single uninterrupted 60 cm-to-DOCK or out-of-view search-to-dock pass.

### E12第七轮独立近距任务：板上DOCKED，尺量与J3差异保留 / Seventh E12 independent near-target task: board DOCKED, ruler/J3 discrepancy retained

**中文**

`build/remaining_20261104/integrated_blue4_e12_tolerance30_final_approach.jsonl`从约41 cm位置**重新按实体POWER**开始独立任务，仍用**tune3/3/5/4/30、pulse200/200/60/6、15.1秒扫描预算**。记录**385C/52B**，host START、synthetic写入、heartbeat均0；结果**DOCKED_OBSERVED**，taskObservationSeconds **14.885635秒**，cleanupErrors为空。没有新RTL、SOF、构建或R6。

首见ARM在观察器时间**40.6648686秒**，APPROACH4/4、J3 **416 mm**；首见DOCK在**52.4846055秒**，J3 **292 mm**，即首见ARM至DOCK约**11.8197369秒**。随后**22个DOCKED快照跨3.065829秒**，均未ARM、无permit、左右0、zeroSent=true、健康锁定，J3均292 mm。该段证明板上自主进入DOCK并保持零速状态，而不是主机先STOP后补记DOCK；zeroSent和状态驻留仍不等于独立测得机械停车延迟。

过程先4/4（D416），再近距右纠偏4/5（D381）并于D339进入ACQUIRE；随后多次反向ALIGN/ACQUIRE，B位置约U163/164→162→161→158→152→140/141，最后回到90–150居中带。**没有LOST或SEARCH样本**，因此本轮不能作为失锁恢复或搜索功能验收。全部ARM期间来源健康、测距有效，没有HOLD/IR/fatal，scanElapsed为0；52个B样本未见候选或传输故障。最终横向框U58–225完整，但纵向触V319下边缘，不能描述成四边都留有余量。C/B独立冻结，也不把邻近采样当成同一帧轨迹。

| 停车距离来源 | 本轮结果 | 含义 |
|---|---:|---|
| J3板上读数 | 292 mm（29.2 cm） | 首DOCK及22个DOCKED快照一致 |
| 用户按“探头前端到纸板”尺量 | 约37 cm（370 mm） | 用户本轮实体测量反馈，未改成35 cm |

两者相差约**78 mm**，原因尚未确定；不平均、不选择其中一个覆盖另一个，也不据此宣称精确35 cm停靠或已完成超声绝对精度标定。该轮实际范围是**约41 cm重新启动后的已见目标停靠**，不能与第六轮被主机中断的625→440 mm段拼成一次60 cm到DOCK的连续自主任务。随后第八轮画外搜索的独立INCOMPLETE结果见下文；本轮成功不覆盖前五轮失败、取消的蓝5/6地面测试或尚未完成的画外搜索停靠。

**English**

`build/remaining_20261104/integrated_blue4_e12_tolerance30_final_approach.jsonl` started a **new physical POWER task** from approximately 41 cm, still using **tune3/3/5/4/30, pulse200/200/60/6 and a 15.1-second scan budget**. It retained **385C/52B snapshots**, with zero host START, synthetic writes and heartbeat commands. Outcome was **DOCKED_OBSERVED**, taskObservationSeconds **14.885635**, and cleanupErrors empty. There is no new RTL, SOF, build or R6 run.

The first ARM sample was at observer time **40.6648686 seconds**, APPROACH4/4 and J3 **416 mm**. First DOCK was at **52.4846055 seconds**, J3 **292 mm**, giving approximately **11.8197369 seconds from first observed ARM to DOCK**. Subsequently **22 DOCKED snapshots spanned 3.065829 seconds**, all disarmed, without permit, both commands zero, zeroSent=true and healthy/locked, with J3 consistently 292 mm. This establishes autonomous board transition to DOCK and a retained zero state, rather than host STOP followed by a claimed docking result. zeroSent/state dwell is still not an independently measured mechanical stopping delay.

The sequence included 4/4 at D416, near right correction 4/5 at D381, and ACQUIRE at D339, then repeated opposite-direction ALIGN/ACQUIRE. B positions progressed approximately U163/164→162→161→158→152→140/141, ending inside the 90–150 centred band. **No LOST or SEARCH was sampled**, so this does not validate loss recovery or search. Every armed sample had a healthy source and valid range, with no HOLD/IR/fatal and scanElapsed0. The 52 B samples showed no candidate or transport fault. The final horizontal box U58–225 was complete, but its vertical extent touched V319; it did not have clearance on all four sides. C/B snapshots freeze independently and are not merged into a single-frame trajectory.

| Stopping-distance source | This trial | Scope |
|---|---:|---|
| J3 board reading |292 mm (29.2 cm) | First DOCK and all 22 DOCKED samples agreed |
| User's ruler measurement from probe front to board |Approximately 37 cm (370 mm) | Actual user measurement, not rewritten as 35 cm |

The difference is approximately **78 mm**, with cause unresolved. The readings are not averaged or substituted for one another, and do not establish exact 35 cm docking or ultrasonic absolute-accuracy calibration. This is **visible-target docking in a fresh task from approximately 41 cm**; it cannot be joined to the sixth host-interrupted 625→440 mm segment to fabricate a single uninterrupted 60 cm-to-DOCK task. The subsequent eighth outside-view search remained INCOMPLETE, as recorded below. This success does not override the first five failures/limited diagnostics, waived blue5/6 ground tests or unvalidated out-of-view search-to-dock.

### E12第八轮画外搜索：找到并恢复目标，但反复对准未停靠 / Eighth E12 out-of-view search: discovery and recovery worked, but repeated alignment prevented docking

**中文**

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

**English**

`build/remaining_20261104/integrated_blue4_e12_tolerance30_search_to_dock.jsonl` used **tune3/3/5/4/30, pulse200/200/60/6 and a 15.1-second scan budget**, retaining **671C/84B snapshots** with zero host START, synthetic writes or heartbeats. taskObservationSeconds was **60.1513566**, outcome **INCOMPLETE**, with reason “60 s task observation limit reached during vision read”. The host's 60-second window expired during B read; this is not the product's 120-second deadline or DOCKED. cleanupErrors was empty. Final state was VISION_ONLY, disarmed, no permit, zero wheel commands, zeroSent=true and J3 **390 mm**, with IR0/sonarHold0.

Initial SEARCH requested `+3/−3` for an accumulated **2.553478 seconds** before finding blue4, leaving **12.546522 seconds** of scan budget. There was **no later SEARCH or reverse SEARCH**. Snapshots retained seven APPROACH segments, eighteen ALIGN segments and six LOST segments; all six losses recovered through ACQUIRE without another search revolution. This is board evidence of recovery with unexhausted budget, not stable mechanical tracking or completed docking. Segment counts are sampled groups, not every native transition or pivot pulse.

B positions lingered near U195 for approximately 10 seconds and U65 for approximately 5 seconds, ending U124→176→171 beyond the tracking-correction bound 165. The user observed blue4 sliding to the VGA right edge after discovery, turning with forward movement and crossing to the left edge, then gradually returning but still near the right edge with a small gap. Repeated crossing remains a limitation; healthy input/recovery does not establish resolved overshoot. J3 approximately 628→390 mm is a probe-direction range change, **not proof of 238 mm vehicle translation**.

The user reported **approximately 47 cm from camera to marker**, while final **J3 was 390 mm**. These have different origins/directions, so they are not a shared-baseline error, ultrasonic calibration or values to average. Trial seven's 292/370 mm readings were both explicitly referenced to the probe front and remain discrepant; they must not be confused with this camera-distance estimate.

| Follow-up trial | Observed outcome | Scope retained |
|---|---|---|
| Sixth tolerance30 diagnostic | User-confirmed continuous correction with 5/4→5/5→4/4 requests | Host STOP at first LOST; later recovery/DOCK unobserved and exact lost B frame unavailable |
| Seventh independent approximately 41 cm task | DOCKED_OBSERVED, 22 zero snapshots over 3.065829 seconds | J3292/probe-front ruler approximately 370 mm unresolved; not joined to trial six |
| Eighth out-of-view search | Discovery after 2.553478 seconds; six LOST segments recovered through ACQUIRE, without later SEARCH | INCOMPLETE 60.1513566 seconds, repeated ALIGN/edge crossing, no DOCK; camera 47 cm/J3390 mm have different baselines |

These follow-up records are committed after trial eight, preserving the earlier five failures/limited diagnostics. Only **turn3→4** was subsequently changed, producing **tune3/4/5/4/30, pulse200/200/60/6 and 15.1 seconds** for a separate ninth isolation of at most 15 seconds; the previous snapshot left it pending; its limited diagnostic result is recorded below, without full-task acceptance. This changes coarse ALIGN's second stage while retaining the fixed 3 small-error rule. It is not a verified recommendation or completed main task. The SOF and product PDF are unchanged, with no recompilation or additional R6 execution claimed.

### E12第九轮turn4隔离：方向改善获反馈，进入接近通道即停车 / Ninth E12 turn4 isolation: improved direction reported, stopped on entry to approach

**中文**

在相同E7070012中只改**turn3→4**，配置为**tune3/4/5/4/30、pulse200/200/60/6、扫描15.1秒**，没有RTL、SOF或构建变化。`build/remaining_20261104/integrated_blue4_e12_turn4_reverse_align15s.jsonl`结果**ALIGN_CORRIDOR_OBSERVED**，taskObservationSeconds **1.7750441秒**，共**1228C/111B**；绝大部分快照用于等待实体POWER，首见ARM在观察器时间**115.1999995秒**，不能把等待时间或总快照数写成持续运动时长/采样率。

直接采到`ALIGN −4/+4 → ACQUIRE 0/0 → APPROACH 4/5`，首次APPROACH触发诊断主机STOP。起步kick6未被这次稀疏轮询采到，不能由配置值补造完整6→4实板命令序。B为U171→164，末VISION_ONLY、未ARM、左右0、zeroSent=true、J3约388 mm，cleanupErrors为空，**没有DOCKED**。用户原话：“**更稳定，并且能向中间移动，但没能居中**”。该观察支持本轮有可接受的方向改善，不能升级为精确居中、持续闭环或通用推荐。

之后独立静止`e12_after_turn4_alignment_preflight.json`取得**3/3健康锁定U147，J3分别379/379/383 mm**，该预检位置位于允许居中带90–150。它与任务中的U164是不同采集时点，不能组合成已测机械停稳曲线、精确停止延迟或同帧前后关系。随后同一参数的第十轮完整画外搜索仍INCOMPLETE，详见下文；本轮有限诊断不替代该任务。

**English**

Only **turn3→4** changed on the same E7070012, giving **tune3/4/5/4/30, pulse200/200/60/6 and a 15.1-second scan budget**, without RTL, SOF or build changes. `build/remaining_20261104/integrated_blue4_e12_turn4_reverse_align15s.jsonl` ended **ALIGN_CORRIDOR_OBSERVED**, taskObservationSeconds **1.7750441**, retaining **1228C/111B snapshots**. Most samples waited for physical POWER; first ARM was at observer time **115.1999995 seconds**. Waiting time or total snapshot counts must not be interpreted as continuous motion time or sampling rate.

The directly sampled chain was `ALIGN −4/+4 → ACQUIRE 0/0 → APPROACH 4/5`, with the first APPROACH deliberately triggering diagnostic host STOP. Kick6 was not sampled in this sparse read sequence, so the configured value does not supply missing evidence of a complete 6→4 board-command transition. B moved U171→164; cleanup left VISION_ONLY, disarmed, both commands zero, zeroSent=true and J3 approximately 388 mm, with empty cleanupErrors and **no DOCKED**. The user reported: “更稳定，并且能向中间移动，但没能居中” — more stable and moving toward the centre, but not yet centred. This supports improved direction in this diagnostic, not precise centring, sustained closed-loop completion or a generally validated recommendation.

The later independent stationary `e12_after_turn4_alignment_preflight.json` recorded **three healthy locks at U147, J3 379/379/383 mm**, placing that preflight inside the 90–150 centred band. It is a different capture time from U164 during the task and cannot establish a measured settling curve, exact stop latency or same-frame relationship. The subsequent tenth full out-of-view search with the same settings remained INCOMPLETE, as recorded below; this limited diagnostic does not replace it.

### E12第十轮完整搜索仍未完成：逻辑5/5不等于物理直行 / Tenth E12 full search remained incomplete: logical 5/5 is not physical straight travel

**中文**

`build/remaining_20261104/integrated_blue4_e12_turn4_search_to_dock.jsonl`使用**tune3/4/5/4/30、pulse200/200/60/6、扫描15.1秒**，记录**613C/79B**，host START、synthetic写入和heartbeat均0。首见ARM在观察器时间**24.2043404秒**、SEARCH状态、J3约699 mm。taskObservationSeconds **60.0024068秒**，结果**INCOMPLETE**；主机60秒观察限到期，不是产品120秒任务时限或正常DOCK。cleanupErrors为空，最终VISION_ONLY、未ARM、左右0、zeroSent=true、J3约**524 mm**，IR0、sonarHold0。

用户原话：“**一直左右调，哪怕居中后还继续调到另一边边缘，并不会往前直走**”。机器多次采到APPROACH5/5，但邻近B坐标出现U141→201、U119→76、U114→196、U143→60的明显跨画面变化。离散C/B快照不是同一原生帧，不能据此精确重建每次物理偏转时刻；不过该命令与实物反馈的不一致必须保留。**相等的左右逻辑请求不证明两轮实际速度相等、车身直行或转向后的机械运动已停止**，不把“读到5/5”写成前进效果通过。

第九轮短诊断“更稳定”的用户反馈不被删去，但其有限观察也不覆盖第十轮长任务中的反复横向调整。当前组合仍属于实验记录，不推广为推荐参数；没有DOCK或完整搜索停靠通过。后续暂不继续长时间实车试跑，转为只读核查ALIGN到前进的命令顺序及起步不均，尚不把软件转序、底盘响应、供电或机械差异中的任何一个写成已确定根因。此轮没有修改RTL、SOF、产品PDF或重新执行R6。

**English**

`build/remaining_20261104/integrated_blue4_e12_turn4_search_to_dock.jsonl` used **tune3/4/5/4/30, pulse200/200/60/6 and a 15.1-second scan budget**, retaining **613C/79B snapshots** with zero host START, synthetic writes or heartbeats. First ARM was at observer time **24.2043404 seconds**, in SEARCH with J3 approximately 699 mm. taskObservationSeconds was **60.0024068**, outcome **INCOMPLETE** at the host's 60-second observation limit, not the product's 120-second deadline or normal DOCKED. cleanupErrors was empty; final state was VISION_ONLY, disarmed, zero wheel requests, zeroSent=true, J3 approximately**524 mm**, IR0/sonarHold0.

The user reported **“一直左右调，哪怕居中后还继续调到另一边边缘，并不会往前直走”** — it kept adjusting left/right, even crossing from the centre toward the opposite edge rather than travelling straight ahead. APPROACH5/5 was repeatedly sampled, but nearby B coordinates jumped U141→201, U119→76, U114→196 and U143→60. Discrete C/B snapshots are not the same native frame and do not precisely reconstruct each physical deflection. Nevertheless, the difference between commands and observed movement must remain explicit. **Equal logical wheel requests do not prove equal actual wheel speeds, straight vehicle motion or mechanical settling after turning.** Reading 5/5 is not a successful physical forward-motion check.

Trial nine's limited report of improved stability is preserved without extending it to the repeated lateral adjustments during trial ten. This remains an experimental configuration, not a recommendation. No DOCKED or complete search-to-dock pass was obtained. Long physical runs are paused while read-only analysis examines ALIGN-to-forward sequencing and uneven startup; software sequencing, chassis response, supply or mechanical differences are not yet established as the root cause. No RTL, SOF, product PDF or R6 execution changed in this trial.

### 第十轮补充：单侧实际运动与底盘固件语义未核实 / Trial-ten clarification: one-sided physical response and unverified chassis semantics

**中文**

用户进一步确认：**“请求了，但实际几乎只动了一边”**。因此本轮缺陷不仅是泛称“不直走”，还包括相等逻辑请求下明显不对称的实物响应；当前没有独立轮速反馈证明左右匹配。

截至2026-11-05核查，官方[General_Driver速度入口](https://github.com/waveshareteam/ugv_base_general/blob/main/General_Driver/movtion_module.h#L275-L303)仅mainType3启用PID，其余含UGV02/mainType2将输入乘512及左右倍率后交给PWM；官方[ROS_Driver速度入口](https://github.com/waveshareteam/ugv_base_ros/blob/main/ROS_Driver/movtion_module.h#L246-L268)则启用PID。这说明官方源码存在不同控制路径，不能只凭接口单位标签认定现场固件行为。

本文和日志的**cm/s是FPGA名义请求单位**，后续OLED已确认UGV Rover/version0.9，但已安装镜像与源码的对应、具体运行语义和实际轮速仍待核实；见后续零速流量记录。本记录不据现象直接断言PI积分问题、电机损坏或某个软件根因，也没有修改或刷写底盘固件。既有实物现象与各轮结果保留，后续核查另列。

**English**

The user further confirmed: **“请求了，但实际几乎只动了一边”** — the request was issued, but almost only one side actually moved. This is more specific than generic failure to travel straight: equal logical requests had visibly asymmetric physical responses, without independently measured matching wheel speeds.

The official [General_Driver speed entry](https://github.com/waveshareteam/ugv_base_general/blob/main/General_Driver/movtion_module.h#L275-L303) enables PID only for mainType3; other types, including UGV02/mainType2, scale input by 512 and side gains into PWM. The official [ROS_Driver speed entry](https://github.com/waveshareteam/ugv_base_ros/blob/main/ROS_Driver/movtion_module.h#L246-L268) enables PID instead. These differing official paths were checked on 2026-11-05; an interface unit label alone does not identify installed behaviour.

Here, **cm/s denotes the FPGA's nominal request units**. The later OLED check confirmed UGV Rover/version0.9; installed binary/source correspondence, runtime semantics and actual wheel speeds remain unverified, as distinguished in the stationary traffic record below. This record does not diagnose PI/integral behaviour, damaged motors or a particular software root cause, and no chassis firmware was changed or flashed. Prior physical observations remain intact, with further investigation recorded separately.

### 第十轮只读协议审计：健康输入及停车到前进边界 / Trial-ten read-only protocol audit: healthy input and stopped-to-forward boundaries

**中文**

独立审计得到**447个ARM期间C样本**，全部sourceHealthyFresh、distanceValid、selectionMatches=true；IR/HOLD/fatal/RX framing error均false。79个B样本全good/fresh，无candidate overflow/error/overrun或transportFaultSticky；completionDiscard=0，bufferDrop始终为历史值2、没有新增丢弃。处理时间39.309–50.810 ms、快照采集年龄41.410–88.097 ms只对应这些采样，不是图像变化到轮子响应延迟。

可见状态分段为SEARCH2、ALIGN21、APPROACH4、LOST9、ACQUIRE27；都是离散采样分段数，不是精确全状态次数。累计SEARCH **5.155026秒**，余**9.944974秒**，所有已采SEARCH均+3/−3，没有反向SEARCH或DOCK。最终B为U60、横向框U11–109，J3最终524 mm。

七组同段ALIGN直接采到kick6→cruise4（反向5组、正向2组），之后有零请求；这是板上状态/命令证据，**没有实机TX逐位解码，也不能推出精确脉宽或实际轮速**。四个APPROACH入口都为5/5，各入口之前最近C样本均是ACQUIRE、左右0、zeroSent=true、uartBusy=false。总共14个APPROACH样本中11个5/5，另有4/5两次、5/4一次；它支持发送侧已呈现停车完成到前进的边界，仍不证明机械已停稳或两轮同步起步。

此次只读审计没有找到能由已采证据证明的命令发送侧bug；这不是对所有未采时序的排除，也不等于完整控制策略无问题。结合用户“几乎只动一边”的反馈，下一步需先核对已安装底盘固件语义与实际响应，保持根因未定，不继续把逻辑速度请求直接当作实测车轮速度。

第十轮后首次OLED读取只见`AP:UGV`、`ST:OFF`和**11.27 V**，当时没有启动车型/Version；MAC不写入记录。单个电压读数不构成低电故障结论。后续只准备核对启动信息；截至本快照没有底盘flash、PID/PWM或车型配置写入。

两个只读代码审查分别核对：居中退出ALIGN后先zeroSent、1.5秒驻留、新fence三帧再进入APPROACH；同向5/5左右分别编码，没有发现单侧符号翻转；`chassis_command`没有非零指令FIFO，发送一份完整包、STOP优先。28字节在115200 baud的串行时间约2.43 ms，已检查的这一层不支持秒级指令排队解释。既有UART管脚级仿真覆盖相关逻辑，本次未重跑或新增测试，也没有底盘实际ACK/轮速证明。结论仍是**未发现确定的FPGA控制/发包bug，底盘模式及响应待核实**，不是彻底排除FPGA。

**English**

The independent audit identified **447 armed C samples**, all sourceHealthyFresh, distanceValid and selectionMatches=true, with IR/HOLD/fatal/RX framing error false. All 79 B samples were good/fresh, without candidate overflow/error/overrun or transportFaultSticky. completionDiscard stayed 0 and bufferDrop stayed at its historical 2, without an increment. Processing 39.309–50.810 ms and snapshot capture age 41.410–88.097 ms describe these samples, not scene-change-to-wheel-response latency.

Visible state segments were SEARCH2, ALIGN21, APPROACH4, LOST9 and ACQUIRE27; these are sampled segment counts rather than every native transition. Accumulated SEARCH was **5.155026 seconds**, with **9.944974 seconds remaining**. All sampled SEARCH requests were +3/−3, with no reverse SEARCH or DOCK. Final B was U60, horizontal box U11–109, and final J3 was 524 mm.

Seven same-ALIGN kick6→cruise4 sequences were directly sampled, five reverse and two forward, followed by zero requests. These are board-state/command observations, **not bit-decoded physical TX, exact pulse durations or measured wheel speeds**. All four APPROACH entries were 5/5. The nearest preceding C sample for each was ACQUIRE with both commands zero, zeroSent=true and uartBusy=false. Of 14 APPROACH samples, 11 were 5/5, two were 4/5 and one was 5/4. This supports the sampled command-side stopped-to-forward boundary, not mechanical settling or simultaneous wheel startup.

No command-transmission bug was demonstrated by this read-only evidence. That does not exclude unobserved timing or validate the entire control strategy. Together with the user's near-one-sided motion report, it motivates verification of installed chassis semantics and actual response while retaining an unresolved root cause; logical requests are not measured wheel speed.

The first post-trial-ten OLED reading showed only `AP:UGV`, `ST:OFF` and **11.27 V**, without a startup model/Version at that time; the MAC is not retained here. One voltage reading does not establish a low-voltage fault. Startup information is being checked; no chassis flash, PID/PWM or model setting was written in this snapshot.

Two read-only code reviews checked the centred ALIGN exit through zeroSent, 1.5-second dwell and three fresh fenced frames before APPROACH; separate encoding of equal 5/5 requests without an identified one-sided sign reversal; and `chassis_command` sending one complete packet, without a nonzero-command FIFO, with STOP priority. Serializing 28 bytes at 115200 baud takes approximately 2.43 ms, so this inspected layer does not support seconds-long command queuing as the explanation. Existing pin-level UART simulation covers the relevant logic; it was not newly rerun here and does not prove chassis ACK or wheel speed. The conclusion remains **no definite FPGA control/transmission bug found, chassis mode/response unverified**, not complete exclusion of FPGA involvement.

### E12后续非运动核查：OLED版本确认及自动反馈停止 / E12 non-motion follow-up: OLED version confirmed and automatic feedback stopped

**中文**

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

**English**

The user read **UGV Rover / version0.9** on the startup OLED. Earlier OLED voltage was 11.27 V; a later page displayed `{"T":1001,"L":0,"R":0,"r":-1.184410511,"p":0.192824244,"v":11.17282963}`. This is user-observed page data, **not a T131-specific ACK or host-recorded live wheel-speed trace**. Zero L/R does not validate moving closed-loop speeds, and one voltage reading does not establish a low-battery fault. The displayed version is confirmed, but the installed binary has not been read and matched to a source commit.

After the user restarted the chassis, the **same original E7070012 SOF** was reprogrammed, then VISION_ONLY and **tune3/4/5/4/30, pulse200/200/60/6, scan15.1 seconds** were restored. Evidence is in `program_e12_after_ugv_version_check_console.log` and `e12_after_ugv_restart_*_console.log`. There was no new RTL, SOF compilation or R6, no ESP chassis flashing, and no PID or model-setting change.

| Independent stopped RX observation | FPGA timeUs | chassisRxCount | Evidence |
|---|---|---|---|
| `e12_ugv090_rx_preflight.json`, sample1 |233294191 |1523 | V1, disarmed, zero commands and zeroSent |
| Same file, sample2 |233631613 |5232 |3709 new bytes over 337422 µs, approximately 10992.2 B/s |
| Same file, sample3 |233980951 |9079 |3847 new bytes over 349338 µs, approximately 11012.3 B/s |
| Five samples in `e12_ugv090_rx_after_flowoff.json` |641121327→642654185 |1230 in all five |No increment over approximately 1.533 seconds; V1/disarmed/zero/zeroSent throughout |

The counter wrapped between the files. **Do not subtract across files or treat 9079→1230 as traffic/loss.** Between those independent windows, the user sent `GET /js?json={"T":131,"cmd":0}` from a phone, disabling automatic feedback only in the current chassis RAM state. The unchanged later RX counter independently establishes that effect instead of relying on a page ACK. FPGA feedback was already 0 and the host sent no active T130 query. This is stationary traffic evidence, not proof that one-sided motion, overshoot or docking has been repaired.

Official 0.90 [serialCtrl](https://github.com/waveshareteam/ugv_base_ros/blob/53c25eb5007e73779ad54526c89bb1b738f1dd1d/ROS_Driver/uart_ctrl.h#L503) accepts consecutive newline-delimited JSON. The [T131 dispatch](https://github.com/waveshareteam/ugv_base_ros/blob/53c25eb5007e73779ad54526c89bb1b738f1dd1d/ROS_Driver/uart_ctrl.h#L66) and [feedback-mode function](https://github.com/waveshareteam/ugv_base_ros/blob/53c25eb5007e73779ad54526c89bb1b738f1dd1d/ROS_Driver/ugv_advance.h#L365) change the feedback switch, whose default is enabled. The [PID_v2 sampling gate](https://github.com/imax9000/Arduino-PID-Library/blob/master/PID_v2.cpp#L26) defaults to 100 ms; a 60 ms kick could be superseded before computation for some phase alignments. This is **a mechanism inference, not demonstrated field causality** or a diagnosis of integral failure.

A same-version, three-stage fixed-coordinate command-change check of at most 4 seconds is planned with real J3/IR protection. It subsequently ran as trial1 and ended early at the actual 500 mm clearance guard, as recorded below; no complete motion PASS is claimed. Stationary traffic and subsequent physical motion will remain separate evidence.

### 关闭反馈后的连续改值trial1：前两段请求已保持，第三段被距离规则终止 / Continuous command-change trial1 after flow-off: first two requests held, third ended by clearance guard

**中文**

本次是独立**CHASSIS_INJECT**隔离检查：固定合成视觉坐标进入真实C控制器/FSM，再经真实安全保护和UART输出；**没有直接写左右轮速或伪造超声距离**，不是相机标牌闭环任务。`e12_continuous_command_preflight.json`两个独立样本均为真实J3 **717 mm**、VISION_ONLY、未ARM、zeroSent=true、RX1230。自动反馈已关闭，本轮RX计数也维持1230。

`build/remaining_20261104/e12_continuous_command_flowoff_trial1.jsonl`记录**46个C样本、一次host START**。在同一活动任务中，阶段1合成U120对应**5/5**请求，已采保持**1.0229965秒**；阶段2合成U80对应**5/4**请求，已采保持**1.0288990秒**。这些是状态中的逻辑请求保持时长，不能直接当作两轮实际速度持续时间。第三段恢复同速没有完整完成；独立协议核查确认第三段4次5/5快照跨约198.598 ms，但不足完整1秒，不补造完整三段通过。

结果为**INCOMPLETE**，原因为`ProbeStopped: real measured J3 clearance must be >500 mm`；真实测距达到**500 mm**时触发诊断专用距离规则，主动结束。它不是J3近障HOLD、IR急停或主任务停靠失败。cleanupErrors为空；最终VISION_ONLY、未ARM、permit0、左右0、zeroSent=true、J3 **500 mm**、IR0、sonarHold0、RX1230。717→500 mm只是测距变化，不能写成精准移动217 mm或据此反算实际车速。

helper的预算从START请求开始最多4秒，预留最后0.5秒发送STOP；阻塞中的JTAG调用及清理可能跨过主机时间边界，因此不等于已量得机械4秒硬停止。此helper和7项fake传输检查仅为ignored `build/`中的实验工具，不属于新增生产RTL验证；本版源码、SOF和R6均未变。trial1用户未仔细观察、没有物理验收；关闭反馈是否改善运动未获结论，不宣称运动问题已修好。

**English**

This is an independent **CHASSIS_INJECT** isolation: fixed synthetic coordinates feed the real C controller/FSM, real safety gates and UART. **Neither wheel requests nor ultrasonic distance were directly overridden.** It is not a real-camera marker task. Two independent `e12_continuous_command_preflight.json` samples showed actual J3 **717 mm**, VISION_ONLY, disarmed, zeroSent=true and RX1230. Automatic feedback was off and the trial's RX count also stayed 1230.

`build/remaining_20261104/e12_continuous_command_flowoff_trial1.jsonl` retained **46 C samples and one host START**. Within the same active task, phase1 synthetic U120 produced **5/5** requests held in sampled state for **1.0229965 seconds**; phase2 U80 produced **5/4** held for **1.0288990 seconds**. These are logical request-state durations, not measured wheel-speed durations. The third return-to-equal-speed phase was not completed; independent protocol review found four brief third-phase 5/5 samples over 198.598 ms, without a complete one-second hold or three-phase pass.

Outcome was **INCOMPLETE**, with `ProbeStopped: real measured J3 clearance must be >500 mm`. Actual measured clearance reached **500 mm**, triggering the diagnostic's own guard. It was not near-obstacle HOLD, IR emergency stop or a failed docking task. cleanupErrors was empty; final state was VISION_ONLY, disarmed, no permit, both requests zero, zeroSent=true, J3 **500 mm**, IR0/sonarHold0 and RX1230. The 717→500 mm range change is not measured 217 mm translation or a basis for exact vehicle speed.

The helper budgets at most 4 seconds from the START request and reserves the final 0.5 seconds for STOP; an outstanding blocking JTAG operation or cleanup may extend beyond that host boundary. It does not measure a mechanical hard-stop deadline. This helper and seven fake-transport checks are experimental files under ignored `build/`, not new production-RTL validation. Source, SOF and R6 are unchanged. The user did not watch trial1 closely, so it has no physical acceptance; improved motion after flow-off and resolution of the motion issue are not established.

### 关闭反馈后的连续改值trial2：三段请求完整观察与有限物理确认 / Continuous command-change trial2 after flow-off: complete holds and bounded physical confirmation

**中文**

trial1用户明确表示没有仔细看，因此**没有获得物理验收**，并要求复演。协议复核在trial1第三段读到**4个5/5快照、首末约198.598 ms**，但没有完成该段完整1秒；原INCOMPLETE及距离诊断停止结果保留，不能补成三段通过。

复演记录`build/remaining_20261104/e12_continuous_command_flowoff_trial2.jsonl`仍使用合成视觉→真实C/FSM→真实J3/IR保护→UART，**只发一次host START**。结果为**THREE_PHASE_REQUESTS_OBSERVED**，共**60个C快照**；同一活动任务内三段完成如下：

| 阶段 | 合成U | 板上逻辑请求 | 已观察保持时长 |
|---|---:|---|---:|
| 1 | 120 | 5/5 | 1.040495秒 |
| 2 | 80 | 5/4 | 1.0156123秒 |
| 3 | 120 | 5/5 | 1.0268218秒 |

最终VISION_ONLY、未ARM、permit0、左右0、zeroSent=true、J3 **855 mm**、RX **1230**、IR0、sonarHold0，cleanupErrors为空。自动反馈持续关闭；没有用直接轮速命令绕过C控制链，也没有注入假距离。三段状态请求完整观察只证明本轮名义请求转换，不等于实际轮速、位移、转弯幅度或用户已经看清；**trial2用户已确认较快→较慢→较快→停车**，更精确范围见后续独立审计。这不是相机目标跟踪、停靠或关闭反馈导致运动问题修复的独立证明。源码/固件/编译/R6未新增，本次物理反馈和独立审计已补齐，按这一有限范围发布记录。

**English**

The user explicitly did not watch trial1 closely, so it **has no physical acceptance**, and requested a replay. Protocol review found **four third-phase 5/5 snapshots spanning approximately 198.598 ms** in trial1, but not a complete one-second third hold. Its original INCOMPLETE/diagnostic-clearance stop remains; it is not retroactively turned into a three-phase pass.

The replay, `build/remaining_20261104/e12_continuous_command_flowoff_trial2.jsonl`, again used synthetic vision→real C/FSM→real J3/IR protection→UART, with **one host START**. Outcome was **THREE_PHASE_REQUESTS_OBSERVED**, retaining **60 C snapshots**. The same active task completed these sampled holds:

| Phase | Synthetic U | Board logical request | Observed hold duration |
|---|---:|---|---:|
| 1 |120 |5/5 |1.040495 seconds |
| 2 |80 |5/4 |1.0156123 seconds |
| 3 |120 |5/5 |1.0268218 seconds |

Cleanup left VISION_ONLY, disarmed, no permit, both commands zero, zeroSent=true, J3 **855 mm**, RX **1230**, IR0/sonarHold0 and empty cleanupErrors. Automatic feedback remained off. No direct wheel command bypassed C and no fake distance was injected. Complete request holds establish this nominal sequence, not measured wheel speed, travel or turning magnitude; **the trial2 user confirmed faster→slower→faster→stopped**, with the bounded scope recorded in the independent audit below. This is not real-camera tracking/docking acceptance or proof that flow-off fixed motion. Source, firmware, compilation and R6 are unchanged; the physical report and independent audit are now retained for this bounded publication.

### trial2物理反馈与独立审计：连续三段变速和停车已观察 / Trial2 physical report and independent audit: three speed stages and stopping observed

**中文**

用户反馈：**机器人较快行驶一段→较慢行驶一段→恢复此前较快行驶→目前已停**。因此可以确认本次连续请求变化确实反映为可见的三段运动变化及停车；用户没有分别确认两轮一直转动、微转方向或精确速度，不能把该反馈升级为左右5/4差速量值验收。没有同条件flow-on对照，也不能认定关闭自动反馈已经修复原来的单侧运动/对准问题。

独立审计确认trial2的60C中**54个ARM样本均处于APPROACH**，请求顺序只有5/5→5/4→5/5，三段保持1.040495/1.0156123/1.0268218秒。ARM期间来源健康、目标锁定、租约有效，IR/HOLD/fatal均0；**全部60个C样本RX恒1230**。START请求至STOP请求**3.4557113秒**，最终零速确认约**3.5274695秒**，在本次4秒主机预算内；这不是实际机械制动时间的独立测量。cleanupErrors为空，最终V1未ARM、左右0、zeroSent、J3约855 mm。

两次模板commit ACK到首次读到新请求分别约**132.4/141.3 ms**，包含主机轮询和合成报告成帧/确认，不是底盘接收或机械响应延迟。复演前独立`e12_continuous_command_replay_preflight.json`两组蓝4健康锁定U84、真实J3 **1249 mm**；这个预检与trial1的717 mm不是同一摆位，任何测距变化均不用于反算精确实车位移/速度。

本次记录到此可确认**连续改值+三段变速+停车在该隔离检查中已观察**，仍非相机跟踪停靠或完整主流程通过。trial1“没仔细看”及其未满第三段的结果保留。下一步只准备单次ALIGN→zero/驻留→APPROACH的最小过渡诊断，尚无结果，不继续60秒长任务；仍使用E7070012，不新增版本、RTL编译或生产R6。实验helper及fake检查仍留在ignored build中。

**English**

The user reported **faster travel→slower travel→return to the earlier faster travel→stopped**. Continuous request changes therefore visibly affected this trial's motion and stopping. The user did not separately confirm uninterrupted motion of both wheels, the small steering direction or exact speeds; this is not quantitative 5/4 wheel-differential acceptance. Without a matched flow-on comparison, it does not establish that disabling automatic feedback fixed the original one-sided motion/alignment problem.

Independent audit found **54 armed samples, all APPROACH**, among 60 C snapshots, with only 5/5→5/4→5/5 requests and holds of 1.040495/1.0156123/1.0268218 seconds. Armed source/lock/lease remained valid, IR/HOLD/fatal were 0, and **RX stayed 1230 in all 60 C samples**. START request to STOP request was **3.4557113 seconds**, with final zero confirmation at approximately **3.5274695 seconds**, within this run's 4-second host budget. This is not an independent mechanical braking-time measurement. Cleanup was error-free, leaving V1/disarmed/zero/zeroSent and J3 approximately 855 mm.

The two template-commit ACKs to first observed new requests took approximately **132.4/141.3 ms**, including host polling and synthetic report generation/confirmation, not chassis or mechanical latency. The separate replay preflight `e12_continuous_command_replay_preflight.json` recorded two healthy blue4 locks at U84 and actual J3 **1249 mm**. This differs from trial1's 717 mm setup, and range differences are not converted into exact vehicle translation or speed.

The bounded conclusion is **continuous changes, three visible speed stages and stopping observed in this isolation**, not camera-guided docking or the complete main task. Trial1's missing physical observation and incomplete third hold remain unchanged. A minimal single ALIGN→zero/dwell→APPROACH isolation and one independent real-camera search were subsequently executed, as recorded below; they are not joined into one continuous task. Firmware remains E7070012 with no new version, RTL compilation or production R6; experimental helper/fake checks remain under ignored build.

### E12单次转向到前进：完整零速驻留后恢复，两轮参与运动获确认 / E12 single turn-to-forward transition: complete zero dwell and both wheels reported moving

**中文**

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

**English**

`build/remaining_20261104/e12_single_turn_to_forward_flowoff_trial1.jsonl` is a separate CHASSIS_INJECT isolation, not the real-camera search. Fixed synthetic coordinates pass through the real C/FSM, real J3/IR protections and UART; neither wheel requests nor distance are directly overridden. E12 and tune3/4/5/4/30, pulse200/200/60/6 and the 15.1-second scan basis are unchanged, with chassis RAM automatic feedback off. This trial uses one host START, synthetic target updates and lease maintenance; the real-camera trial's zero-injection/zero-heartbeat scope does not apply here.

Independent protocol review confirmed **SINGLE_ALIGN_ZERO_FORWARD_REQUESTS_OBSERVED**, with **60 C snapshots / 54 armed**. One sampled ALIGN episode was followed by ACQUIRE and APPROACH, with no second ALIGN, SEARCH or LOST samples:

| Stage | Directly sampled requests/state | Limit of the evidence |
|---|---|---|
| One ALIGN | Two 6/−6 samples, then two 4/−4 | Consistent with two-stage requests; not measured wheel speed or physical TX bit decoding |
| Stopped reconfirmation | 31 ACQUIRE samples with both requests0, zeroSent=true and UART idle | Local zero-packet completion, not measured mechanical settling time |
| Forward | 19 APPROACH samples, all5/5, spanning0.920350 seconds | Sampled request duration, not precisely one second of physical straight travel |

Natural ACQUIRE and zero-packet completion occurred **0.267321 seconds** after START. The first TX5 changing synthetic U to120 was only requested at **0.311450 seconds**, with commit ACK at **0.343871 seconds**, so an early target change did not truncate the turn. Zero confirmation to first APPROACH was **1.611663 seconds**. ACQUIRE frames208/209 were healthy/observed with lock cleared; frame211 restored lock and APPROACH, consistent with production fresh-three-frame requalification after dwell, without directly sampling the single-cycle fence. An outstanding C read crossed the intended forward cutoff by approximately34.774 ms; this is not an exact physical pulse measurement. START request to STOP request was **2.799345 seconds**, with final zero confirmation at approximately **2.842336 seconds**, within this run's six-second host budget.

Armed source/lease, valid non-FAR distance and physical selection stayed healthy; IR/HOLD/fatal/framing-error were0. The normal lock clearing during ACQUIRE is not reclassified as a motion-loss fault. RX stayed1230 in all60 C samples. Cleanup was error-free, ending in VISION_ONLY, ARM0/permit0, both requests0, zeroSent=true/UART idle and J3 **730 mm**.

The user reported **both wheels moving together**. This supports both wheels participating in this single check, with no one-sided-only response reported. The user did not separately describe each turning direction, straight-line accuracy or precise duration; those results are not inferred. Without a matched flow-on comparison, feedback shutdown is still not established as the cause of a repair. This isolation does not replace camera-guided discovery, continuous tracking or docking acceptance.

### E12关闭反馈后的真实相机搜索：60秒仍未停靠 / E12 real-camera search after feedback shutdown: no docking within60 seconds

**中文**

随后独立真实相机任务记录在 `build/remaining_20261104/integrated_blue4_e12_flowoff_search_to_dock.jsonl`。E12源码、SOF及上述运行参数未改变。本轮 **729 C / 90 B**，任务观察 **60.0067485秒**，结果 **INCOMPLETE**；未读到DOCKED或其他终态，观察窗结束后由主机STOP收尾。host START、合成写入和heartbeat均为 **0**，与上面的注入隔离任务分开计算。

收尾cleanupErrors为空，VISION_ONLY、ARM0、permit0、左右0、zeroSent=true，J3 **407 mm**，IR0/HOLD0。用户看到找到蓝4后慢慢修正，牌边先靠VGA右边、再靠左边，最终蓝4居中；过程中有反复修正，最后一段两轮共同前进后停，但用户对末段是否又大幅纠偏不确定。相机到标牌垂直尺量46 cm与J3末407 mm来自不同起点，不能作同基准误差计算。最后停车是60秒观察窗host STOP，不是DOCKED；关闭反馈没有证明完整搜索停靠通过，也没有同条件flow-on对照证明因果修复。详细协议审计将在下段保留。忽略目录中的旧observer仅将Quartus会话启动timeout临时设为10秒，入Session后恢复2秒；这不改变生产程序或本轮60秒运动观察预算。没有为微测试重新编译、生成SOF或重复打ZIP。

**English**

The following independent real-camera task is recorded in `build/remaining_20261104/integrated_blue4_e12_flowoff_search_to_dock.jsonl`, with unchanged E12 sources/SOF and the same runtime settings. It retained **729 C / 90 B** snapshots over **60.0067485 seconds** of task observation and ended **INCOMPLETE**. No DOCKED or other terminal state was observed before host STOP at the observation limit. Host START, synthetic writes and heartbeat commands were all **0**, counted separately from the injected isolation above.

Cleanup was error-free, leaving VISION_ONLY, ARM0/permit0, both requests0, zeroSent=true, J3 **407 mm**, IR0/HOLD0. The user saw discovery followed by gradual repeated correction: the marker first reached the VGA right side, then the left, and finally appeared centred. Both wheels advanced together in the last segment before stopping; the user was uncertain whether another large final correction occurred. The perpendicular camera-to-marker ruler distance was46 cm, while final J3 was407 mm; the different origins prevent a same-baseline error calculation. Final stopping was host STOP at the60-second observation limit, not DOCKED. Feedback shutdown has not established full search-to-dock acceptance or causal repair without a matched flow-on control. Detailed independent review follows below. The ignored observer only temporarily allowed ten seconds for Quartus session startup, restoring two seconds once in-session; this did not change production logic or the60-second task observation budget. No new compilation, SOF or repeated ZIP was produced for these micro-tests.

#### 真实搜索的独立审计：拒识和短转中断仍在，不能归结为传输断流 / Independent real-search audit: rejected targets and interrupted turns remain, without evidence of a transport outage

**中文**

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

**English**

Among **469 armed C snapshots**, directly sampled contiguous state segments were SEARCH3, ACQUIRE27, ALIGN18, LOST15 and APPROACH4. These are sparse observed segments, not exact action or UART-packet counts. The15 APPROACH samples contained only **one5/5**, plus four5/4, two4/5 and eight4/4; this run cannot be described as sustained5/5 while continuously turning. The longer equal-request interval had six4/4 samples at task-relative47.276–47.798 seconds, with nearby B readings changing from129 to87/64. Non-simultaneous C/B samples do not directly quantify mechanical response.

| Item | Recorded evidence | Scope |
|---|---|---|
| Search | Three segments, all+3/−3;1.433652 seconds accumulated,13.666348 remaining, no reverse SEARCH | Scan budget was not exhausted; no DOCKED |
| Source validity | Three of469 armed samples had sourceHealthyFresh=false, all in zero/zeroSent ACQUIRE | Frames45034/45117/45129, inputAge54–77 ms; their raw B frames were not sampled, so acquisition timeout is not established |
| LOST entries | All15 had sourceHealthyFresh=true;12 had observed/locked both false, three retained observed but lost lock | Source-health or transport interruption does not explain every loss |
| B frames and processing | All90 B snapshots frameGood/fresh, no candidate/transport faults, constant drop3 and discard0 | Processing38.818–57.066 ms and snapshot age40.020–92.062 ms are not wheel-response latency |
| Safety and feedback | Armed ranges valid and selections matched; IR/HOLD/fatal/framing-error all0; RX1230 in all729 C samples | Feedback remained off, without proving the motion cause removed |

Blue4 readings progressed U53→85→142→185, remained near185–194 for an extended interval, then returned through129→64→77→final129. Some main candidate boxes nearU185 were139..230 or140..231, leaving8–9 pixels on the right while NF/reason4 was already present; later U192 boxes146..238 and U194 boxes149..239 approached the edge. NF was mostly reason4, with one reason3 and one reason1. **Not every rejection can therefore be called image clipping.** Changing target validity contributes to reconfirmation, but its complete visual/mechanical causes are not isolated.

Eleven of18 sampled ALIGN segments were followed by LOST. For six, the first sample was still kick6 and the board-time difference to the next LOST was96.095–122.530 ms. Combining this with the maximum60 ms kick bounds their start-to-interruption time above by156.095–182.530 ms, before the nominal200 ms endpoint. This is **logical evidence that target validity interrupted at least those six segments early**, not a complete physical pulse-width or wheel-stop measurement. CCTL polling can miss short states; inter-sample intervals are not exact transmission or mechanical delays.

The conclusions remain separate: both wheels participating in one isolated transition were confirmed by the user; the real-camera task still repeatedly aligned/rejected targets without DOCKED and finally stopped through observation-window cleanup. There was no matched flow-on control and no established cause. This batch changes no RTL, startup initialization or firmware version; any subsequent discussion of brief-NF handling is not an implemented repair.

### E13：定向及R6通过，整板时序失败，未下载 / E13: focused/R6 pass, full-build timing failure, never programmed

**中文**

用户授权的有限ALIGN失锁处理已落实到候选源码，BUILD_ID为 **E7070013**；正式整机顶层显式启用`ALLOW_BOUNDED_ALIGN_GAP`，旧参数兼容入口默认关闭。进入转向仍须新鲜锁定；只有原定ALIGN时长非零且 **≤200 ms** 才取得有限继续资格。健康短暂NF或同身份重新获取期间，保持已锁存的原方向、速度阶段及截止时间，不延长、不重新kick、不改向；**配置超过200 ms仍执行原先的持续锁定要求，不把整个300 ms设置都放宽**。可信有效观测跨越允许居中边界可提前停；缺失报告的旧坐标不能伪装成跨越。来源/选择/配置/帧质量/歧义/时效和原IR/J3安全条件仍优先，结束后完整零速ACQUIRE重确认。APPROACH失锁立即停车规则不变。

`build/remaining_20261104/align_continuity_e13_20261104T212612021761Z/verified_result.json`从原成功日志独立确认定向 **PASS**：新`tb_align_continuity`在TURN_SIGN−1/+1下各 **553项检查、60条UART解码**；关闭新连续性例外的旧`tb_control_repair`基线 **2041项检查、500条UART解码**。此旧基线的`STRICT_ALIGN_BAND=0`、`RUNTIME_TUNING=1`，不是旧110–130窄居中档。定向运行记录总耗时 **21.4837644秒**，最终编译/三配置日志均0 errors/0 warnings。HOST_RUNNER另有 **18项PASS**。这些均是主机/RTL证据，不是底盘实际轮速、机械过冲或停靠验收。

历史失败没有覆盖：原`result.json`因末端PASS字符串匹配漏掉冒号，把已经输出`PASS: tb_control_repair`的成功旧基线误记FAIL；`verified_result.json`只重新核对原日志，**没有重跑仿真或覆盖原FAIL文件**。此前测试台曾错误地把mode2中不适用的`cameraAbandon`作为来源故障，随后改用适用的`interactionBusy`；另一个32位回绕用例的早期失败也保留，修正细节待独立说明。不得把本次记录写成“无失败尝试”。

正式fresh课程R6已 **PASS，223.568636秒**，目标285秒、targetMet=true、cleanBuild=true；**62个新鲜source、14项正常PASS＋1项mutant CAUGHT、退出0、jobs4**。结果为`build/member_b/20261104T212711_301457Z_verilator_course/result.json`。哈希复用仍只发生在当次运行、精确source匹配条件下；新增测试进入正式回归，没有削减旧场景、帧数或断言。

E13的完整编译已结束，最终为 **FAIL**：`build/member_b/20261104T212541_740043Z_build/result.json`记录compile1309.487秒、Quartus返回0，但wrapper检测到Critical Warning332148和负setup裕量而拒绝通过。最差slow85 setup **−0.279 ns**、slow0 **−0.246 ns**，hold **+0.214 ns**；ALM29610/32070（92%）、41152寄存器、M10K357/397、DSP51/87。独立post-fit门检没有继续运行，**E13未下载、未实机，不提供可用发布SOF**。当前最后确认实板仍是E7070012，E12的真实flowoff搜索60.0067485秒未DOCK结论不变。

只读STA诊断将关键链定位为 `chassisDebugControl|mode[0] → chassis_u|shreg[19]`，经感知有效性、运动请求、安全许可和轮速ASCII转换，共21逻辑级；不是已锁存短转截止比较器。E14将signed7-bit合法轮速−15..15的绝对值/十进制串行运算改成等价查表；32768种左右/enable组合完整232位报文相等的定向验证通过，但最终时序改善必须由E14实际拟合确认。没有放宽时序约束或把仿真通过当成可下载许可。

最后迭代明确为 **E7070014**。用户允许同一最终SOF增加停车调参，以完成真实SW→红2→搜索→跟踪/前进→DOCK及近障/IR保护；E14完整构建、R6和实机验收仍待。新增策略范围和默认差异见README开头。最终ZIP等最终实际结果形成后统一打包；R5正式一页表已补齐字段，未实测成绩/等级仍PENDING。

**English**

The authorized bounded ALIGN target-loss handling is implemented in candidate sources with BUILD_ID **E7070013**. The production integrated top explicitly enables `ALLOW_BOUNDED_ALIGN_GAP`; the legacy parameter entry defaults it off. Entry still needs a fresh lock, and only a nonzero originally scheduled ALIGN duration **≤200 ms** earns continuation eligibility. During healthy brief NF or same-identity reacquisition, the latched direction, speed phases and deadline remain unchanged: no extension, re-kick or reversal. **Configurations above200 ms retain the original continuous-lock requirement; the entire300 ms range is not relaxed.** A trusted valid observation crossing the allowed centring boundary can stop early; stale coordinates from an absent report cannot masquerade as a crossing. Source/selection/configuration/frame-quality/ambiguity/age and original IR/J3 safety checks remain dominant, followed by complete zero-speed ACQUIRE reconfirmation. APPROACH still stops immediately on target loss.

`build/remaining_20261104/align_continuity_e13_20261104T212612021761Z/verified_result.json` independently confirms focused **PASS** from existing successful logs: new `tb_align_continuity` at TURN_SIGN−1/+1 each passed **553 checks and60 UART decodes**; the old `tb_control_repair` baseline with the new continuity exception disabled passed **2041 checks and500 UART decodes**. That baseline used `STRICT_ALIGN_BAND=0` and `RUNTIME_TUNING=1`, not the old110–130 narrow centring band. The recorded focused run elapsed **21.4837644 seconds**, with0 errors/0 warnings in the final compile/three configurations. HOST_RUNNER separately passed **18 checks**. These are host/RTL results, not actual chassis speeds, mechanical overshoot or docking acceptance.

Earlier failures remain preserved. The original `result.json` mismatched a final PASS string by omitting the colon, marking the already successful `PASS: tb_control_repair` legacy run FAIL. `verified_result.json` rechecked those same logs **without rerunning simulations or overwriting the original FAIL file**. An earlier testbench incorrectly used `cameraAbandon` as a source-fault stimulus in mode2, then changed to applicable `interactionBusy`; an earlier32-bit-wrap test failure also remains, with its correction details awaiting independent explanation. This is not reported as a first-attempt/no-failure result.

The fresh formal course R6 **passed in223.568636 seconds**, against285 seconds, with targetMet=true and cleanBuild=true: **62 fresh sources,14 normal PASS plus one mutant CAUGHT, exit0, jobs4**. Evidence is `build/member_b/20261104T212711_301457Z_verilator_course/result.json`. Hash reuse remains limited to exact source matches within the current run. The new test is included in formal regression without removing earlier scenarios, frames or assertions.

E13 full compilation finished **FAIL**. `build/member_b/20261104T212541_740043Z_build/result.json` records1309.487 seconds of compile and Quartus return0, but the wrapper rejected Critical Warning332148 and negative setup slack. Worst slow85 setup was **−0.279 ns**, slow0 **−0.246 ns**, hold **+0.214 ns**; ALM29610/32070(92%),41152 registers,M10K357/397,DSP51/87. The independent post-fit gate did not run. **E13 was never programmed or physically tested and has no usable released SOF.** E7070012 remains the last confirmed image; its60.0067485-second feedback-off search still did not DOCK.

Read-only STA traced the worst chain from `chassisDebugControl|mode[0]` to `chassis_u|shreg[19]`, through perception validity, wheel requests, safety permission and ASCII conversion,21 logic levels. It is not the latched turn-deadline comparator. E14 replaces serial absolute-value/decimal operations for legal signed7-bit speeds−15..15 with an equivalent lookup. A focused comparison passed all32768 left/right/enable combinations over the full232-bit message, but actual E14 fitting must establish timing improvement. Constraints were not relaxed and simulation is not programming clearance.

The final iteration is now **E7070014**. The user authorized additional stationary tuning in this final SOF for physical SW→red2→search→tracking/forward→DOCK and near-obstacle/IR acceptance. Its full build,R6 and hardware results remain pending. See the opening README section for policy ranges and default distinctions. Final ZIP generation waits for the actual final results. The standalone one-page formal R5 sheet includes the required fields; unmeasured scores/grade remain PENDING.

<a id="limitations"></a>

## 已知限制与未验证范围 / Known limitations and unverified scope

**中文**

- E12第五轮仍反复对准并边缘丢牌，重搜未找回后进入J3近障HOLD；未DOCK。有限回正获得用户接受，命令两段转序已有实板证据，但不代表轮速一致或主线通过。第六轮tol30已观察连续差速修正，首次LOST即诊断STOP；第七轮约41 cm独立任务已DOCKED，J3292与用户尺量370 mm差异未定；第八轮画外搜索仍INCOMPLETE60.1513566秒；第九轮turn4有限回正获反馈、首次APPROACH即STOP；第十轮完整搜索INCOMPLETE60.0024068秒；5/5逻辑请求不证明物理直行。

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

**English**

- E12's fifth trial still repeatedly aligned, lost the target at an image edge, failed to reacquire it and entered J3 near-obstacle HOLD without DOCKED. The user accepted limited realignment and board commands demonstrate two stages, but wheel-speed matching and the main task are not validated. The sixth tolerance30 diagnostic observed continuous differential correction before host STOP at first LOST; the seventh independent POWER task from approximately 41 cm reached DOCKED in 11.8197369 seconds from first ARM, retaining 22 zero-state DOCK snapshots for 3.065829 seconds. J3 read 292 mm while the user measured approximately 370 mm from the probe front; the discrepancy is unresolved. The eighth outside-view search remained INCOMPLETE 60.1513566 seconds; tasks are not joined. The ninth turn4 diagnostic reached the approach corridor and host-stopped; the tenth full search remained INCOMPLETE 60.0024068 seconds, without verified straight travel.

- E11 original/search3 searches ended NOT_FOUND; turn3/turn5 isolation remained INCOMPLETE. Turn5 recorded LOST→ACQUIRE with budget remaining, but twitching, centre-crossing and target loss remain. The final 3/5/4/3/40 session-only comparison also remained INCOMPLETE. Testing concludes without RTL changes or a search-to-dock pass claim.

- E10 found and locked the initially unseen target and briefly entered APPROACH, but then lost it and resumed searching. This run ended NOT_FOUND/SCAN_BUDGET without docking. The user confirmed the fixed target and final standstill; reverse SEARCH was not triggered, leaving its physical recovery effectiveness unverified.
- Historical search4 has three complete-revolution observations and a 13.6-second record. Current search3 has only two single circles plus one double-circle reference, supporting the conservative 15.1-second budget. Precise 360° and automatic fixed-time stopping-angle error remain unmeasured, as does the laboratory epoxy surface. The first two starts surged on one side and translated 3.5/2 cm, with the cause unisolated. Blue5/6 lack individual ground-task evidence because the user cancelled those separate trials. Precise 350 mm stopping error, complete task time and image-change-to-UART latency remain incompletely measured; accumulated command time is not heading feedback.
- E5's real blue1 task did not dock, with alignment oscillation, lost locks and scan-budget exhaustion. E7 trials 01–05 also did not complete docking: windows without ARM, cable/near-range interruption, asymmetric short movements and crossing the centre remain recorded. E6 passed functional simulation but failed timing and was never programmed. E7's own R6, Full Compilation/post-fit and programming resolved timing acceptance without establishing a physical control fix. The basically-straight two-second run is isolation evidence; E8's continuous differential steering passed focused checks, 270.641086-second formal R6, Full Compilation/post-fit and programming/readback, with stationary blue1 lock 4/4. The first real blue1 task recorded board-level DOCKED and approximately 3.18 seconds disarmed/zero, with the user confirming continuous forward travel, no obvious veering and an approximately 335 mm endpoint. Final alignment/reconfirmation still took about 25 seconds; approximately 1 cm extra left-wheel travel is only an uncertain user estimate. Blue2 recorded a red2 event/relock/ARM, with separate user-reported forward travel and stopping outside the observation window plus a later terminal snapshot. Its missing continuous motion log is not reconstructed into a full closed-loop or precise-error claim. Blue3 now has this run's complete physical POWER/real approach/slowing/differential-correction/docking record and user feedback. Blue4 also docked, retaining startup jerk/rightward drift, approximately 17.1 seconds of final correction and slight residual rightward position. The user cancelled separate blue5/6 ground tasks in this run; they are no longer scheduled work, but still have only static vision coverage without individual ground-task evidence. The initially-out-of-view blue4 trial was executed but failed to maintain a lock, ending automatically disarmed/zero in SCAN_BUDGET/NOT_FOUND. This requirement has not passed. E9 bounded reverse-recovery source is frozen and focused regression and formal R6 passed. Full Compilation/post-fit and programming/identity verification have also passed. This run's initially-out-of-view trial is INCOMPLETE: it found/locked the target but did not reach DOCKED within the 60-second observation window, then host STOP ended the run. No reverse SEARCH occurred, leaving physical reverse recovery unverified; earlier pre-locked-target docking cannot replace that evidence.
- Physical J3 protective stop, hysteresis, recovery and docking states have the E4 raised-wheel evidence above. E4's first ground run recorded actual invalid distance triggering HOLD/zero. E5 returned FAR in all 6 real open-space samples with its display confirmed, and the three ground trials included 10/13/15 FAR motion snapshots without HOLD. Long-term continuity and the real visual closed loop still need verification. Ruler-checked 250/300/350 mm boundaries and absolute ranging accuracy remain outstanding. FAR is not a measured four metres, and the old 4000/validfalse state does not identify a unique electrical cause.
- SW6 colour information and automatic page alternation, plus SW7 “no marker” over a gap and `ID:B1` over centred blue1, have physical confirmation. UNKNOWN/rejection-reason display, all 16 slots occupied together and centre ambiguity still require verification.
- Three static SW8 normal/bypass vision pairs are complete. Matched closed-loop comparisons during ground motion, sustained movement, occlusion and varied lighting still require follow-up measurement. Ground scanning, SW6/7 and other ongoing acceptance work will be updated from their own records; the static comparison does not establish their completion.
- Fragmented red backgrounds can still exceed active-label capacity. Current bad frames revoke permission; recovery is possible from E3 onward, but persistently invalid images do not become valid automatically. Cropping, glare, blur and duplicate targets can be rejected.
- The historical frame251 model accepts all eight official markers. Frame30321 still rejects fragmented blue6 under its original red41/blue33 profile. One offline comparison kept the original pixels and only lowered blue to 20, restoring all eight accepts; the current real six-card scene also accepted all six at red57/blue37. Stability across lighting/threshold conditions still needs verification; historical inputs and digit6 answers were not fabricated.
- The user confirmed physical E4 red2 starting and stopping when blue1 left the view. LOST/ACQUIRE intermittency remains, so sustained target visibility needs improvement. That run's independent physical timing of the host's two-second STOP remains unmeasured. Later HOLD03 independently verified explicit STOP and no restart with continuing input/lease, with physical stopping confirmed; mechanical stopping latency and wheel direction in that run were not measured. Final state is VISION_ONLY, disarmed and logical zero speed, with standstill confirmed; this does not establish floor docking acceptance.
- A/C member SIDs must still be supplied by the members. Course/IP notices and AI-assisted-change attribution remain; human sign-off is not invented.

<a id="files"></a>

## 管脚与文件 / Pins, files and ownership

**中文**

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
| `docs/ECHO7_Integrated_Datasheet.pdf` | 两页：产品操作指南＋正式R5指标页 |
| `docs/ECHO7_R5_Datasheet.pdf`、`docs/R5_TARGETS.md` | 独立一页课程R5表及指标/来源说明；export绑定独立R5 PDF |
| `docs/REPAIR_RESULT.md`、`VERSION_README.md`、`OWNERS.md` | 分版本结果、迭代记录及来源/成员归属 |

保留工程、RTL/TB、runner、真实相机输入/model/replay、最终SOF及报告所需测量值。编译数据库和仿真缓存不作为源码；不新增逐文件SHA清单或重复凭据包。原课程/IP声明保留；A/C成员SID待补，不虚构归属或人工签核。

**English**

| Interface | FPGA signal | Pin |
|---|---|---|
| IR receiver | IRDA_RXD | PIN_AA30 |
| J3 TRIG / ECHO | GPIO_1[27] / GPIO_1[29] | PIN_AJ22 / PIN_AG22 |
| UGV02 UART TX / RX | GPIO_1[31] / GPIO_1[33] | PIN_AF23 / PIN_AD21 |

J3 uses the RCWL-1601, 3.3 V and common ground. Connect FPGA TX to chassis RX and FPGA RX to chassis TX. No J4 sensor has been added. Camera/VGA pins are defined by the QSF. The 24-bit B/C request, 141-bit report, 76-bit status and shared microsecond clock all reside in CLOCK_50. Real IR/J3 remain outside the synthetic vision source.

| Path | Purpose |
|---|---|
| `rtl/top/echo7IntegratedTop.sv` | Production three-mode top, source switching and board wiring |
| `rtl/capture/`, `rtl/vision/`, `rtl/tracking/` | Camera transport, colour/candidates/projective recognition and target reports |
| `rtl/interaction/` | Red1 calibration, fresh red2 presentation and event handshakes |
| `rtl/member_c/` | Selection adapter, task FSM, IR/J3 protection and UART chassis commands |
| `rtl/debug/` | BCTL/CCTL, synthetic vision and VGA sample diagnostics |
| `tests/`, `run_all_tests.sh` | Module/system self-checks, real-input fixtures and the formal R6 entry |
| `tools/chassis_debug.py`, `tools/echo7.py` | Persistent JTAG, injection, build, programming, calibration and real capture |
| `tools/compare_observations.py`, `tools/export_submission.py` | Offline paired SW8 summaries from physical-selection observations and integrated single-SOF ZIP export |
| `firmware/E7070012/PartBDebug.sof` | Current E12 release SOF copied from the successfully compiled and programmed artifact; the unresolved search-to-dock limitation is retained |
| `docs/ECHO7_Integrated_Datasheet.pdf` | Two pages: product operation guide plus formal R5 metrics |
| `docs/ECHO7_R5_Datasheet.pdf`, `docs/R5_TARGETS.md` | Standalone one-page course R5 datasheet and metric/provenance notes; export binds the standalone R5 PDF |
| `docs/REPAIR_RESULT.md`, `VERSION_README.md`, `OWNERS.md` | Version-specific results, iteration history and source/member attribution |

Retain project sources, RTL/testbenches, runners, real camera inputs/models/replay, the final SOF and measurements needed for reporting. Build databases and simulation caches are not source. No new per-file SHA inventory or duplicate evidence package is introduced. Original course/IP notices remain, A/C SIDs remain pending, and member attribution or human sign-off is not fabricated.
