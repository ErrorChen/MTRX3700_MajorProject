# Member B / Member C 当前接口契约 v2

**本文件是本次蓝色车位 1–6、固定机位、可对折 A4 场景的权威设计契约，可直接作为 B 与 C 的分工和接口开发依据。** B 负责识别、语音数字提议和视觉跟踪；C 决定是否接受提议、选择哪个目标，并独立负责导航与运动。本文件没有运动实现，也不表示对应 RTL、语音模型或板级验证已经完成。

任务输入曾引用 `reference_interfaces/` 中的代码、规范和 64 组 **v1 历史示例**；该目录并未随当前迁移检出提供。不得把旧示例的 1–3 默认配置、75 bit 状态或功能牌离场规则当作当前契约。当前交接以本文为准；实现与测试应逐项对应本文，不以旧示例通过代替 v2 通过。

2026-11-02 实现状态：当前已加入 v2 共享 package、视觉核心、目标跟踪、固定纸面交互和无运动 C 模拟器，并执行对应模型及 RTL 自检。用户最新要求将真实语音输入后移，当前通过 C 模拟器直接 SELECT 1–6；这类接口激励不属于语音识别证据。当前源码映射、实际验证层级及硬件限制统一记录在 [主 README](README.md) 与 [版本 README](VERSION_README.md)。本文仍是唯一 B/C 行为契约，协议版本不因测试后移而改变。

## 1. 版本与本次固定配置

| 项目 | v2 约定 |
|---|---|
| `PERCEPTION_CONTRACT_VERSION` | 2；B、C 和调试解码器必须使用同一个版本 |
| `DEFAULT_ACTIVE_BAY_MASK` | `10'b0001111110`，即 `10'h07E`，只启用 1、2、3、4、5、6 |
| 数字类型 | bayId 仍为 4 bit，类型可表达 0…9；本次 0、7、8、9 未启用 |
| 无 ID | `INVALID_BAY_ID = 4'hF`；数字 0 不代替 CLEAR |
| 当前场景模式 | `fixedSheetMode=1`；作为 B 的构建/配置选项，不增加一条 C 控制通道 |
| 原生图像 | 320×240，原生像素坐标 x=0…319、y=0…239 |
| 对外坐标 | 保持 v1 的 240×320 坐标框架，变换见第 5 节 |
| 三个事务 payload | targetRequest=22 bit；targetReport=139 bit；userEvent=104 bit，字段顺序与 v1 相同 |
| `status` | **76 bit**；保留 v1 全部字段，在结构末尾增加 `speechArmed` 1 bit |
| 新状态编码 | `INTERACTION_SPEECH_ARMED = 4'd9`；原状态 0…8 的编码保留 |

协议版本与 `configVersion` 是不同概念：协议版本描述字段布局和语义；configVersion 是运行时实际生效的识别配置版本。v2 的状态布局和固定纸面交互语义均有变化，所以必须升级版本，不能只把 v1 的 mask 改成 1–6 后继续称 v1 兼容。

不额外增加逐包协议版本字段；同一 FPGA 内由共同 package 固定版本 2，并在集成检查中验证 `$bits` 为 22、139、104、76。JTAG/软件状态头须公开 contractVersion=2，解码器拒绝未知版本。旧 75 bit status 不能直接接到新 76 bit status 后依赖隐式补位继续使用。

## 2. 同步边界、信号方向与复位

边界只使用 `CLOCK_50` 上升沿。B 内部承担相机 PCLK、音频时钟及显示时钟的 CDC；C 不直接读取相机域 held bus。

| 信号 | 位宽 | 驱动方向 | 单位与语义 |
|---|---:|---|---|
| `CLOCK_50` | 1 | 顶层 → B/C | 共享 50 MHz 时钟 |
| `reset` | 1 | 顶层 → B/C | **同步、高有效**，共同复位 |
| `timeUs` | 32 | 顶层 → B/C | 同一微秒计数器，模 2³² 递增；共同复位归零 |
| `interactionEnable` | 1 | C → B | 允许功能牌开启交互及维持语音武装；为 0 时撤销武装并取消未完成交互 |
| `interactionPermit` | 1 | C → B | C 已确认静止且允许实际颜色取样或话语采集/处理；撤销规则见第 8 节 |
| `targetRequest` | 22 | C → B | 选择/清除目标记录 |
| `targetRequestValid` | 1 | C → B | 当前提供一条请求 |
| `targetRequestReady` | 1 | B → C | 本拍可接收请求 |
| `targetReport` | 139 | B → C | 某一实际采集帧的目标结果 |
| `targetReportValid` | 1 | B → C | 当前提供一条报告，**不代表看到了目标** |
| `targetReportReady` | 1 | C → B | 本拍可接收报告 |
| `userEvent` | 104 | B → C | 一次校色或话语交互的终结事件 |
| `userEventValid` | 1 | B → C | 当前提供一条事件 |
| `userEventReady` | 1 | C → B | 本拍可接收事件 |
| `status` | 76 | B → C | 同步注册的实时状态，不另设 ready/valid |

modport 方向沿用 `perceptionLink.perception`、`controller`、只读 `monitor`。三个 payload 及 status 都按下文表格顺序从高位到低位打包。这是 FPGA 内部逻辑接口，不规定片外串行字节序。

### 2.1 统一握手规则

1. 仅在上升沿 `!reset && valid && ready` 时传输一次。发送者不得等待 ready 才置 valid。
2. `valid && !ready` 后，直到握手或共同复位，valid 保持为 1，整个 payload 保持不变。目标变更、校色提交、许可撤销都不能改写已展示的记录。
3. 复位优先于传输。复位采样边沿，两侧各自驱动的 valid、ready 清零；清空 FIFO、待发报告、帧缓存所有权、跟踪历史及 C 的测量/事件缓存。跨域缓冲中的旧数据也必须失效。
4. 复位恢复缺省颜色配置：activeCfgVersion=0、calibrated=0、speechArmed=0、interactionBusy=0、kind=NONE、state=IDLE；readiness 在链路重新就绪前为 0。目标为空，诊断和序号历史清零。
5. 本协议要求 B/C 共同复位，不支持 B 单独复位而 C 继续沿用旧缓存。没有额外 bootEpoch；若以后需要独立复位，必须另行升级协议并使用能区分重启的监督机制。

## 3. C → B：`targetRequest_t`，22 bit

| 字段，按声明顺序 | 位宽 | 规则 |
|---|---:|---|
| `operation` | 2 | 0=`TARGET_CLEAR`；1=`TARGET_SELECT`；2、3 保留 |
| `requestTag` | 16 | C 为每次新 SELECT/CLEAR 分配；0 合法 |
| `bayId` | 4 | SELECT 仅接受 1…6；CLEAR 忽略此字段 |

请求握手后，C 立即切换自己期待的 requestTag 并清除旧测量缓存。B 清除连续确认历史；新请求经过内部 CDC 确认可安全应用后，从第一个完整采集帧开始绑定新 tag。已经采集/处理的旧帧仍携带旧 tag，不得改贴新 tag。

无效 operation 或未启用 ID 也作为一条控制事务被接收，但 B 清空选择、保留该 requestTag，置 `FAULT_REQUEST_INVALID`，随后报告 targetSelected=0、bayId=15、reason=REPORT_INVALID_REQUEST；不得暗中继续旧目标。合法 CLEAR 后报告 REPORT_NO_SELECTION。

tag 模 2¹⁶ 回绕，按相等匹配当前请求，不按数值大小比较。存在同 tag 的旧事务可能滞留时，不允许复用该 tag。`targetRequestReady` 表示接收控制事务，不表示已经锁定目标；锁定只能由随后真实新帧的报告证明。

## 4. B → C：`targetReport_t`，139 bit

| 字段，按声明顺序 | 位宽 | 规则 |
|---|---:|---|
| `requestTag` | 16 | 该帧绑定的目标请求 |
| `frameId` | 16 | 原始采集帧号，模 2¹⁶；0 合法 |
| `captureStartUs` | 32 | **实际采集该帧 SOF** 的共享微秒时间 |
| `configVersion` | 16 | 该帧真正使用的识别配置版本 |
| `bayId` | 4 | 已选目标 1…6；无选择为 15 |
| `frameGood` | 1 | 整帧、候选、字形及版本一致且可用 |
| `observed` | 1 | 当前帧真实观察到一个唯一、可信的所选编号 |
| `locked` | 1 | 当前观察已通过连续 3 帧确认 |
| `ambiguous` | 1 | 当前存在多个可接受位置声称是所选编号 |
| `targetSelected` | 1 | 当前逻辑目标合法；不代表它可见 |
| `centreU` | 8 | 对外横坐标，0…239 像素 |
| `centreV` | 9 | 对外纵坐标，0…319 像素 |
| `boxWidth` | 8 | 主色区包围盒宽度，有观察时 1…240 像素 |
| `boxHeight` | 9 | 主色区包围盒高度，有观察时 1…320 像素 |
| `quality` | 8 | 有观察时 1…255 的质量分，非概率 |
| `reason` | 8 | 下表枚举 |

| 值 | reportReason 名称 | 含义 |
|---:|---|---|
| 0 | `REPORT_OK` | 当前观察已锁定 |
| 1 | `REPORT_NO_SELECTION` | 未选目标 |
| 2 | `REPORT_ACQUIRING` | 当前有真实观察，尚未确认满 3 帧 |
| 3 | `REPORT_NOT_FOUND` | 当前帧未发现所选目标 |
| 4 | `REPORT_DUPLICATE_ID` | 所选编号在多个位置同时出现 |
| 5 | `REPORT_FRAME_BAD` | 坏帧或帧/附属数据不一致 |
| 6 | `REPORT_CONFIG_CHANGED` | 配置切换使确认历史失效 |
| 7 | `REPORT_REQUEST_CHANGED` | 目标请求切换使确认历史失效 |
| 8 | `REPORT_PIPELINE_NOT_READY` | 当前识别链路不可用 |
| 9 | `REPORT_INVALID_REQUEST` | 请求操作或 ID 无效 |
| 10 | `REPORT_LOW_QUALITY` | 分类或几何证据不足 |
| 11 | `REPORT_RESOURCE_DROP` | 该采集帧因资源不足被弃用 |

**测量不变量：** observed=0 时 centreU、centreV、boxWidth、boxHeight、quality 全为 0，locked=0。observed=1 时必须 frameGood=1、targetSelected=1、ambiguous=0；未锁定使用 ACQUIRING，锁定使用 OK。locked 不能仅由内部身份记忆维持。

连续确认要求三个相邻、不同的采集帧均有有效唯一观察。missing、bad frame、ambiguous、采集帧缺口、新请求或新配置立即把计数和 locked 清零；重新出现后重新确认 3 帧。报告传输次数、重复读取同一快照都不能累加确认。C 因背压漏收报告不等于 B 漏采帧；B 的 locked 由真实采集/处理历史决定。

若所选编号在两处出现，报告 frameGood=1、targetSelected=1、ambiguous=1、observed=0、locked=0，测量量清零，reason=DUPLICATE_ID；不得自动取面积最大或候选列表第一项。多个不同编号同时可见是正常情况。

每个实际完成处理的帧都应有报告，包括未发现目标的帧。候选溢出或错帧数据使整帧无效，不发布部分候选拼成的可信位置。资源不足时报告该实际帧的 RESOURCE_DROP；若连该帧记录也无法送达，C 必须依靠测量年龄过期，不得把上次位置一直当作新观察。

## 5. 坐标、同帧归属、年龄与序号

横向 A4 不改变外部坐标定义。保留原生到 C 的变换 `u=y, v=319-x`；内部数字 ROI 可以旋转以便识别，但最终主色区 bbox 必须转换回本节框架。不得把纸面毫米坐标、格子索引或新的横向显示坐标悄悄写进 centreU/V。

```text
uMin = yMin                 uMax = yMax
vMin = 319 - xMax           vMax = 319 - xMin
centreU = floor((uMin + uMax) / 2)
centreV = floor((vMin + vMax) / 2)
boxWidth  = uMax - uMin + 1
boxHeight = vMax - vMin + 1
```

bbox 端点包含在框内，加法先扩位，中心向下取整。先转换 bbox，再求中心；不能旋转一个已取整的原生中心。例如原生 x=10…13、y=20…24，对外为 centre=(22,307)、宽 5、高 4。公开位置是当前色区框的整数中心，不用白字质心、预测或位置滤波代替当前测量。它不是距离或转向指令。

frameId、captureStartUs、configVersion 和内部缓存 bank 必须共同描述同一帧。时间戳在实际 SOF 获取，经跨域随该帧保存；发布、处理完成、握手、JTAG 文件接收均不能重置它。旧 EPA2 在下一次 frame_start 发布前一帧，所以尤其不能直接拿发布时的新 SOF 时间给旧帧盖章。

年龄计算为无符号 32 bit 模减：

```text
ageUs = (timeUs - captureStartUs) & 0xffffffff
fresh = (ageUs < 0x80000000) && (ageUs <= maxAgeUs)
```

初始 `maxAgeUs=150000`，是待实测调整的预算，不是已经验证的时延保证。age≥2³¹ 视为未来/无效时间。缓存测量每次使用前仍按当前 timeUs 检查；不能只在第一次收到时检查。

帧序用 `delta=(newId-lastId)&0xffff`：0 为重复；1…32767 为更新；32768…65535 拒绝为不可接受顺序。65535→0 合法。超过半序号空间的停顿要先清历史重新获取；共同复位也清历史。重复帧不续期、不再确认一次。eventId 采用同样的模序号去重；requestTag/configVersion/interactionId 主要按当前值相等匹配。所有 16 bit 标识复用前须确保同值旧事务不再滞留。

## 6. 状态：`perceptionStatus_t`，76 bit

| 字段，按声明顺序 | 位宽 | 语义 |
|---|---:|---|
| `interactionBusy` | 1 | 有一项实际校色或话语事务在等待许可、采样、分类或等待终结事件入队 |
| `kind` | 2 | 0=NONE，1=CALIBRATION，2=SPEECH，3 保留 |
| `state` | 4 | 下表状态码 |
| `calibrated` | 1 | 自最近共同复位/显式恢复缺省配置后，至少一次校色成功提交 |
| `audioReady` | 1 | 实际音频采集与当前数字词表可用；不是仅检测到声音 |
| `perceptionReady` | 1 | 当前视觉链路能提供一致结果 |
| `activeCfgVersion` | 16 | 当前生效配置；不是 stalled 旧报告的版本 |
| `reportDropCount` | 16 | 未展示待发报告被替换的饱和计数 |
| `eventOverflow` | 1 | 事件队列容量不足，sticky 到共同复位 |
| `faultFlags` | 16 | 诊断位，sticky 到共同复位 |
| `interactionId` | 16 | 当前或最近一次实际交互的 ID |
| **`speechArmed`** | **1** | 红 2 已成功打开语音入口；是否可实际开始话语还取决于 enable、permit、readiness 和队列空间 |

| state 值 | 名称 | busy / kind 的约束 |
|---:|---|---|
| 0 | `INTERACTION_IDLE` | busy=0，kind=NONE |
| 1 | `INTERACTION_WAIT_PERMIT` | 校色等待许可：busy=1，kind=CALIBRATION；有有限超时 |
| 2 | `INTERACTION_CAL_COLLECT` | busy=1，kind=CALIBRATION |
| 3 | `INTERACTION_CAL_VALIDATE` | busy=1，kind=CALIBRATION |
| 4 | `INTERACTION_CAL_COMMIT` | busy=1，kind=CALIBRATION，等待跨域提交最终结果 |
| 5 | `INTERACTION_LISTEN` | 已开始采集一段实际话语：busy=1，kind=SPEECH |
| 6 | `INTERACTION_CLASSIFY` | busy=1，kind=SPEECH |
| 7 | `INTERACTION_RESULT_QUEUE` | busy=1，kind 为该终结事务的类型 |
| 8 | `INTERACTION_REARM` | busy=0，kind=NONE；固定纸面模式等待话语间静音，不等待红牌离场 |
| **9** | **`INTERACTION_SPEECH_ARMED`** | **busy=0，kind=NONE，speechArmed=1；空闲等声/等许可** |

空闲武装不分配新 interactionId，不预留永久事件槽，不周期性产生“没有说话”事件。翻页不会把 SPEECH_ARMED 变成一个永久 busy 状态。VGA 可以显示当前视觉观察；C 的控制侧使用规则仍见第 10 节。

faultFlags：bit0=CAMERA_TRANSPORT、bit1=CANDIDATE_OVERFLOW、bit2=MASK_BUFFER_OVERRUN、bit3=CONFIG_REJECTED、bit4=AUDIO_CAPTURE、bit5=REQUEST_INVALID、bit6=INTERNAL_PROTOCOL；bit7…15 保留为 0。历史故障位不等于故障仍在持续；readiness 表示当前可用性，未恢复的相关链路必须置 readiness=0。

v2 status 的精确类型如下；其它三个结构按第 3、4、9 节表格顺序声明，字段位宽不变：

```systemverilog
localparam int unsigned PERCEPTION_CONTRACT_VERSION = 2;
localparam logic [9:0] DEFAULT_ACTIVE_BAY_MASK = 10'b0001111110;

typedef struct packed {
    logic interactionBusy;
    interactionKind_t kind;       // logic [1:0]
    interactionState_t state;     // logic [3:0], 新增 4'd9
    logic calibrated;
    logic audioReady;
    logic perceptionReady;
    logic [15:0] activeCfgVersion;
    logic [15:0] reportDropCount;
    logic eventOverflow;
    logic [15:0] faultFlags;
    logic [15:0] interactionId;
    logic speechArmed;            // v2 新增，末尾 1 bit
} perceptionStatus_t;             // $bits == 76
```

## 7. 固定纸面流程与左右翻页保持

本场景同一张纸含左页红 1 双色校色牌、红 2 和右页蓝 1–6。红 1 与红 2 同时可见不构成互斥冲突；按照阶段解释。蓝参考条无数字，不能成为目标。

1. **准备校色。** enable=1 时，连续 3 个有效帧从实际像素识别红 1 及其自身蓝参考区。预留终结事件空位，分配新的 interactionId，busy=1；permit=0 时在 WAIT_PERMIT 等待，permit=1 才开始采样。
2. **提交一次完整校色。** 参考 ROI 必须属于红 1 自身版式，采原始 RGB、检查样本与几何稳定；不能用旧颜色阈值预先排除不符合旧配置的样本。shadow 配置验证成功后，配置与其新版本在同一 SOF 原子生效，CLOCK_50 收到一致确认后更新 status 并入队 CALIBRATION_DONE。清除旧跟踪确认历史；失败保留上一个完整配置。成功后不因红 1 常驻反复校色。
3. **打开语音入口。** 在校色后的配置下，连续 3 个有效帧确实识别红 2 后置 speechArmed=1。进入空闲武装状态时 busy=0；这一步不生成车位提议，也不要求人再次确认。permit 尚未给出时保持武装意图，但不开始话语采集。
4. **处理一段话语。** speechArmed、enable、permit、audioReady 均为 1，静音重新武装条件满足，且有一个终结事件空位时，接受实际语音起点；此刻分配新的 interactionId、预留该事件槽并置 busy=1。采集到终点后分类，一次话语只产生一次成功提议或明确拒识。不得在 CLASSIFY 阶段把下一段声音继续拼入本段。
5. **静音重新武装。** 终结事件入队后 busy=0、kind=NONE；speechArmed 保持 1，经过静音间隔回到 SPEECH_ARMED。不要求红 2 离场，也不要求再次看到红 2 才处理每段新话语。等待声音期间无事件、无持续 busy。

校色等待、有效采样和一次话语采集/分类必须有有限超时，预算写入 B 的配置及实际验证记录。空闲等声本身不作为一次超时交互。校色失败/超时结束本次尝试，不因同一红 1 仍在画面而每帧重复生成错误事件；重新尝试由有记录的显式校色重置/重试流程开放，并仍须看见正确红 1、重新取得真实样本。

### 7.1 对折时保持什么、失效什么

**在左页完成校色和红 2 武装后，翻到右页，已提交的颜色配置与 speechArmed 都继续有效。** 红牌离场本身不清除它们。左/右翻页不是共同复位，也不是“重新校色一次”的信号。

| 情况 | 已提交配置 / calibrated | speechArmed | 当前目标观察 |
|---|---|---|---|
| 红牌常驻、消失或左右翻页 | 保持 | 已武装则保持 | 只看当前可见蓝牌；不可见即 observed=0、locked=0 |
| interactionPermit=0 | 保持；提交竞态见第 8 节 | 可以保持，但停止新话语启动 | 仍按真实当前帧报告；不因此伪造测量 |
| interactionEnable=0 | 保持已提交配置 | 清零，并清空话语起点/静音重新武装历史 | 不暗中清除已选目标；按当前帧报告 |
| 重新 enable=1 | 不自动重复已完成校色 | 必须重新从真实像素识别红 2，才重新武装 | 沿用当前目标请求的观察规则 |
| 显式重做校色 | 保留旧配置直到新提交；失败保留旧配置 | 先清零；成功，或仍保有已校色的旧配置时，重新识别红 2 才能再武装 | 新配置提交时重新确认 3 帧 |
| 显式恢复缺省配置 | 在 SOF 原子切换缺省配置，configVersion 加一，calibrated=0 | 清零 | 旧配置报告失效，确认历史清零 |
| 共同 reset | 缺省配置、version=0、calibrated=0 | 清零 | 选择和缓存全部清空 |

保持规则只适用于已经提交的配置和已经完成的武装；校色尚未完成时移走红 1，若导致参考区几何或样本失效，仍须终止该次校色并报告失败，不能沿用未完成样本。首次校色失败、calibrated 仍为 0 时，不进入固定纸面的语音武装阶段。

显式重试/恢复命令属于有记录的调试配置入口，不增加 targetRequest 的操作码，不允许直接写入“校色成功”或“已识别红 2”。已经选择蓝 3 后，即使翻回左页，targetSelected 仍可为 1，但 observed 必须为 0；回到右页后再由三个真实有效帧重新锁定蓝 3。

## 8. 许可撤销、取消与跨域提交边界

**interactionPermit 不是仅在启动瞬间采样的一次性许可。** 活跃颜色采样/验证、话语采集/分类期间必须持续获准；撤销会取消尚未完成的工作。interactionEnable=0 也会取消活跃交互，并额外清除 speechArmed。

- 校色尚处于 WAIT_PERMIT 时 permit=0 是正常等待；一旦已经开始，permit 撤销即停止继续使用未完成样本，作废未提交 shadow 配置。活跃话语同样停止采样/分类并作废未完成结果。
- 空闲 SPEECH_ARMED 时 permit=0 不产生一条取消事件，因为此时没有正在执行的话语；保留武装意图，暂停新话语起点并清空不完整的起点检测历史。重新许可后要先满足静音条件，再开始新话语。
- 校色提交发生在相机域：**已在提交域同步可见的撤销优先，已经提交的配置不回滚。** CLOCK_50 刚撤销但撤销尚未到达提交域，不能证明提交没有发生。
- 若提交请求正在跨域往返，B 要等待该提交事务的最终“已提交/未提交”结果：已提交则报告 CALIBRATION_DONE 及新版本，未提交的取消则报告 INTERACTION_CANCELLED。不能先宣称取消且未提交，随后又为同一 interactionId 发第二个完成事件。
- 事件已经入队/展示后，即使许可随后撤销，也不得抽走或改写一条 stalled 的 userEvent。C 在 enable/permit 撤销时立即停止接纳语音提议，记录撤销时的 timeUs 为 `cancelCutoffUs`，并记录当时仍活跃的 interactionId 为已取消会话；不必等待取消事件到达才执行拒收。
- 撤销覆盖**撤销前已完成但尚未消费的所有语音提议**，不仅是 status.interactionId 对应的一条。重新许可后，除拒绝已取消会话，还要拒绝 issuedAtUs 在 cancelCutoffUs 之前或同一微秒的旧提议，模时间比较见第 9 节。这样 FIFO 中更早完成的结果不会在下一次许可窗口复活。C 应保持 userEventReady 接收并丢弃这些旧提议，使队列能继续前进。
- C 接受 SPEECH_BAY_REQUEST 时须确认当前 enable=1、permit=1、会话未取消、版本和年龄正确。信息性完成/取消事件可以记录；实际配置状态以一致的 activeCfgVersion/calibrated 为准。

已被 C 接受并发送 TARGET_SELECT 的车位选择不会随随后许可撤销而自动清空。C 若要清除目标，另发 TARGET_CLEAR。交互会话与视觉目标各自有生命周期。

## 9. B → C：`userEvent_t`，104 bit，与队列

| 字段，按声明顺序 | 位宽 | 规则 |
|---|---:|---|
| `eventId` | 16 | 每入队一条事件加一；复位后首个为 1，允许回绕 |
| `eventType` | 4 | 下表枚举；0 不得入队 |
| `bayId` | 4 | 语音提议为 1…6；信息事件为 15 |
| `quality` | 8 | 语音提议为 1…255，非概率；其它事件可为 0 |
| `issuedAtUs` | 32 | 事件形成时的共享微秒时间，不在 FIFO 等待时刷新 |
| `configVersion` | 16 | 事件对应的生效配置；校色完成为刚提交的新版本 |
| `reason` | 8 | 下表原因枚举 |
| `interactionId` | 16 | 本次实际校色或话语 ID；复位后首个为 1，允许回绕 |

| eventType 值 | 名称 | 意义 |
|---:|---|---|
| 0 | `EVENT_NONE` | 保留，禁止入队 |
| 1 | `EVENT_SPEECH_BAY_REQUEST` | 用户提出车位选择，C 接受后另发 SELECT |
| 2 | `EVENT_CALIBRATION_DONE` | 配置已实际提交 |
| 3 | `EVENT_CALIBRATION_FAILED` | 校色失败，旧配置保留 |
| 4 | `EVENT_INPUT_REJECTED` | 一次实际输入被拒识或采音故障 |
| 5 | `EVENT_INTERACTION_CANCELLED` | 未完成事务被撤销 |
| 6 | `EVENT_INTERACTION_TIMEOUT` | 活跃事务超时 |

reason 编码保留：0=OK，1=LOW_CONFIDENCE，2=BAY_DISABLED，3=NO_SPEECH，4=AUDIO_UNAVAILABLE，5=CAL_CARD_INVALID，6=CAL_SAMPLES_INVALID，7=PERMIT_REVOKED，8=ENABLE_REVOKED，9=WAIT_TIMEOUT，10=CAPTURE_TIMEOUT，11=INTERNAL_ERROR；其余保留。成功提议及校色完成使用 OK，其它事件使用对应非零原因。静音空闲不反复产生 NO_SPEECH。

一个实际交互只入队一个终结事件。speechArmed 是持续入口状态，不把每一轮无声等待分配为新 interactionId。事件 FIFO 总容量为 **4 条，包含当前已展示未握手的队首**；实际交互开始前必须预留一个终结事件空位，直到该交互结束。没有位置就不开始新交互，置 eventOverflow；不得覆盖旧事件。静音武装状态不长期占用预留槽，事件满也不能停相机。

目标报告采用一个不可变的正在展示槽和一个“最新待发”槽。反压期间可替换未展示的待发报告，每替换一条 reportDropCount 饱和加一；正在展示的报告绝不改写。事件与报告独立缓冲。

C 按 eventId 去重，语音提议还要检查 interactionId 是当前接受的会话且未被取消、configVersion 是当前版本、ID 已启用。默认事件年龄预算 `eventMaxAgeUs=2000000`，使用与帧相同的模减及未来时间拒绝规则；这仍是待实测调整的预算。旧或取消的语音事件可被握手取走并记录拒收原因，但不能触发新的 SELECT。

撤销前未消费的语音提议按以下规则过滤，不新增接口字段。C 先检查事件年龄，再检查最近一次撤销时间：

```text
sinceCancelUs = (timeUs - cancelCutoffUs) & 0xffffffff
cancelFenceActive = haveCancelCutoff && (sinceCancelUs <= eventMaxAgeUs)
afterCutoffUs = (event.issuedAtUs - cancelCutoffUs) & 0xffffffff
rejectPreCancelProposal = cancelFenceActive
                         && (afterCutoffUs == 0 || afterCutoffUs >= 0x80000000)
```

所有预算都须小于 2³¹ µs。撤销边界同一微秒的结果按旧提议保守拒绝。超过 eventMaxAgeUs 后，撤销前已形成的事件本身必然超龄，此时清除 haveCancelCutoff，避免计数器绕过整圈后旧围栏再次生效；共同复位也清空围栏。若后续再撤销，以最新撤销时刻重新启用围栏。仍活跃的话语可能在撤销之后才形成终结记录，因此**时间过滤不能代替已取消 interactionId 的拒收**。这两项规则与当前 enable/permit、会话、版本、ID 和年龄检查同时成立；信息性校色完成/取消事件可继续记录，不因拒收语音提议而回滚已提交配置或已接受的 SELECT。

## 10. C 的最小消费规则与独立 B 演示

C 接受语音提议后，创建新的 requestTag 并发送 SELECT；B 不在内部绕过 C 自动改变目标。独立 B 台架使用无运动的 C 接口模拟器完成同一过程。通过 JTAG/模拟器直接选择 1–6 只能证明目标选择和视觉链，不能作为麦克风识别证据。

对目标测量，C 的基本可用判定保持为：

```text
currentRequest.operation == TARGET_SELECT
&& currentRequest.bayId in {1,2,3,4,5,6}
&& report.requestTag == currentRequest.requestTag
&& report.bayId == currentRequest.bayId
&& report.configVersion == status.activeCfgVersion
&& report.targetSelected && report.frameGood
&& report.observed && report.locked && !report.ambiguous
&& status.perceptionReady && !status.interactionBusy
&& fresh(report.captureStartUs, timeUs)
```

固定纸面自动交互按本契约先成功校色再武装语音；若 C 的任务政策还要求任何视觉使用都先校色，可额外检查 calibrated。缺省颜色配置产生真实视觉观察与“用户校色已完成”是两件事。

speechArmed=1 的空闲等声期 busy=0，因此不会永久阻止 C 接受视觉观察。实际话语处理或校色期间，视觉仍采集和报告真实结果；C 可继续记录/显示，但不能将 busy=0 或某个事件当作运动许可。B 不提供距离、转向、停车完成或可以行驶的结论。

新请求、新配置、收到当前流的无效/缺失报告和年龄过期都使旧缓存不再可用。旧 tag、旧配置、重复/倒序包不能替换当前有效缓存；缓存仍要独立按当前状态和时间重新检查，避免“没有新包就永远沿用旧位置”。

## 11. 当前交接范围与必须验证的差异

本文固定接口和行为；当前实现使用 `ECHOPHACE1/rtl/member_b/common/perception_pkg.sv` 和 `perceptionLink.sv`。目标跟踪、C 模拟器、固定纸面交互及合成像素核心回放已实际执行 ModelSim 自检；精确测试范围和来源见版本 README 与 `ECHOPHACE1/evidence/member_b/metadata.json`。这不意味着真实麦克风或全部板上验收已经完成，也不继承旧 v1 示例的测试结论。B/C 集成必须使用同一份 v2 package，核对 22/139/104/76 bit 位宽与状态编码。

在原握手、年龄、序号、请求和配置向量之外，v2 必须验证以下变化：

- 1–6 均可 SELECT；0、7、8、9 拒绝；CLEAR 独立生效。
- status 为 76 bit，SPEECH_ARMED=9，空闲 armed 时 busy=0。
- 红 1/红 2 同时常驻：校色一次后才能武装，不相互永久冲突、不重复校色。
- 左页完成校色/武装后翻到右页：配置和 armed 保持，蓝牌按真实帧重新确认；翻回左页目标立即失观测。
- 一次话语一个终结事件，通过静音重武装；无声等待不刷事件、不占住队列。
- permit 撤销取消活跃采样/分类但可保留空闲武装；enable 撤销还须清武装；重新 enable 要重新看到红 2。
- 提交域可见的撤销优先；已提交不回滚；提交往返中最终只产生一个准确终结事件。
- 撤销时已经 stalled 的结果保持稳定；重新许可后，C 同时拒收撤销前队列中更早完成的旧提议，以及撤销后才形成的已取消活跃会话结果。

上述验证应区分参考模型、真实 RTL 仿真、综合时序和板级证据；不能用一层的成功代替另一层。本文件用于用户审阅及后续交接。
