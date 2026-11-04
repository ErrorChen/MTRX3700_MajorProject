`timescale 1ns/1ps
// ECHO-7 production board: separate tracking, task authorization and safety.
// POWER starts a perception-driven task, never direct fixed-speed motion.
// Board I/O wrapper reused from validated Member C; only reset ownership changed.
// KEY1 pages: decimal distance / confirmed out-of-range FAr (d), NEC words (H/L).
// On the H page HEX1..0 is the command byte, code[23:16].
module memberCBoard #(
    // Existing chassis forward convention: both UART wheel signs are negative.
    parameter int LEFT_POLARITY = -1, RIGHT_POLARITY = -1,
    // Candidate image-to-turn convention: must be checked with wheels raised.
    parameter int TURN_SIGN = 1,
    parameter bit RUNTIME_TUNING = 0,
    parameter bit RUNTIME_MOTION_POLICY = 0,
    parameter bit ALLOW_BOUNDED_ALIGN_GAP = 0,
    parameter bit INIT_FLOWOFF = 0,
    // Single safety threshold in mm; stop at distance <= this value.
    parameter int ULTRASONIC_ESTOP_MM = 250, // EB STOP DISTANCE mm
    parameter int HEARTBEAT_CLKS = 10_000_000, // 200 ms at 50 MHz
    parameter int BLINK_CLKS = 2_500_000,      // 50 ms event indication
    parameter int KEY_DEBOUNCE_CLKS = 1_000_000, // 20 ms stable press AND release
    parameter int SELECTION_STABLE_CLKS = 1_000_000,
    parameter int ACQUIRE_SETTLE_US = 1500000, ACQUIRE_TIMEOUT_US = 900000
) (
    input  wire       CLOCK_50,
    input  wire       reset50, // Shared integrated CLOCK_50 reset.
    input  wire [1:0] KEY,
    input  wire       IRDA_RXD,
    input wire [5:0] SW,
    input logic [1:0] mode,
    input logic debugStart,debugStop,modeChanged,rawMode,injectLeaseValid,scanCalibrated,visualStart,
    input logic [31:0] scanBudgetUs,tuningWord,alignTimingWord,motionPolicyWord,
    output logic [511:0] statusWords,
    // Internal public v3 link to perceptionCore, all synchronous to CLOCK_50.
    input logic [31:0] timeUs,
 input logic cameraFifoFault, cameraAbandonEvent, // synchronous CLOCK_50 private safety link
    input perception_pkg::perceptionStatus_t perceptionStatus,
    output perception_pkg::targetRequest_t targetRequest,
    output wire targetRequestValid, input wire targetRequestReady,
    input perception_pkg::targetReport_t targetReport,
    input wire targetReportValid, output wire targetReportReady,
    input  wire       SONAR_ECHO,
    output wire       SONAR_TRIG,
    input  wire       CHASSIS_RX, // former GPIO_1[33], PIN_AD21
    output wire       CHASSIS_TX, // former GPIO_1[31], PIN_AF23
    output wire [9:0] LEDR,
    output wire [6:0] HEX0, HEX1, HEX2, HEX3, HEX4, HEX5
);
    wire nec_valid, nec_repeat;
    wire [31:0] nec_code;
    nec_decoder #(.CLK_HZ(50_000_000)) u_nec (
        .clk(CLOCK_50), .rst(reset50), .ir(IRDA_RXD),
        .valid(nec_valid), .code(nec_code), .repeat_code(nec_repeat));

    logic [31:0] last_code;
    logic code_seen;
    always_ff @(posedge CLOCK_50) begin
        if (reset50) begin
            last_code <= '0;
            code_seen <= 1'b0;
        end else if (nec_valid) begin
            last_code <= nec_code;
            code_seen <= 1'b1;
        end
    end

    // A stable release is required before another debounced page change.
    localparam int KW = (KEY_DEBOUNCE_CLKS > 1) ? $clog2(KEY_DEBOUNCE_CLKS) : 1;
    logic [1:0] key1_sync;
    logic key1_stable;
    logic [1:0] page;
    wire high_page = page==1;
    logic [KW-1:0] key1_count;
    always_ff @(posedge CLOCK_50) begin
        if (reset50) begin
            key1_sync <= 2'b11;
            key1_stable <= 1'b1;
            key1_count <= '0;
            page <= 0;
        end else begin
            key1_sync <= {key1_sync[0], KEY[1]};
            if (key1_sync[1] == key1_stable) key1_count <= '0;
            else if (key1_count == KW'(KEY_DEBOUNCE_CLKS - 1)) begin
                key1_stable <= key1_sync[1];
                key1_count <= '0;
                if (!key1_sync[1]) page <= page==2 ? 0 : page+1'b1;
            end else key1_count <= key1_count + 1'b1;
        end
    end

    wire [11:0] distance_mm;
    wire distance_valid, sample_pulse;
    logic [15:0] decimal_digits;
    integer k;
    always_comb begin
      decimal_digits=0;
      for(k=11;k>=0;k=k-1) begin
        if(decimal_digits[3:0]>=5) decimal_digits[3:0]=decimal_digits[3:0]+4'd3;
        if(decimal_digits[7:4]>=5) decimal_digits[7:4]=decimal_digits[7:4]+4'd3;
        if(decimal_digits[11:8]>=5) decimal_digits[11:8]=decimal_digits[11:8]+4'd3;
        if(decimal_digits[15:12]>=5) decimal_digits[15:12]=decimal_digits[15:12]+4'd3;
        decimal_digits={decimal_digits[14:0],distance_mm[k]};
      end
    end
    wire [15:0] shown = page==0 ? decimal_digits : high_page ? last_code[31:16] : last_code[15:0];
    wire display_blank=page==0 ? !distance_valid : !code_seen;
    // 4000 with valid=1 is the sonar FAR sentinel, never a measured 4 m.
    wire displayFar=page==0 && distance_valid && distance_mm==12'd4000;
    wire [6:0] digitHex0,digitHex1,digitHex2,digitHex3;
    hex_digit h0 (.d(shown[3:0]),   .blank(display_blank), .seg(digitHex0));
    hex_digit h1 (.d(shown[7:4]),   .blank(display_blank), .seg(digitHex1));
    hex_digit h2 (.d(shown[11:8]),  .blank(display_blank), .seg(digitHex2));
    hex_digit h3 (.d(shown[15:12]), .blank(display_blank), .seg(digitHex3));
    assign HEX0=displayFar ? 7'b0101111 : digitHex0; // r, active low
    assign HEX1=displayFar ? 7'b0001000 : digitHex1; // A
    assign HEX2=displayFar ? 7'b0001110 : digitHex2; // F
    assign HEX3=displayFar ? 7'b1111111 : digitHex3;
    assign HEX5 = !statusWords[14] ? (statusWords[15] ? 7'b1000110 : 7'b0101011) :
      page==0 ? 7'b0100001 : high_page ? 7'b0001001 : 7'b1000111; // H / L, active low
    hex_digit mode_hex(.d({2'b00,mode}),.blank(1'b0),.seg(HEX4)); // mode: 0 integrated, 1 vision, 2 injection
    //                         // '-'

    // Confirmed command bytes (not inverse bytes).
    localparam logic [7:0] POWER_CODE = 8'h12;
    localparam logic [7:0] ESTOP_CODE = 8'h0f;
    // NEC repeats and retransmitted full frames refresh the quiet timer. A held
    // POWER therefore cannot both release the IR latch and start a new task.
    logic irSeen;
    logic [7:0] lastIrCommand;
    logic [31:0] lastIrUs;
    wire power_frame = nec_valid && nec_code[23:16]==POWER_CODE &&
      (!irSeen || lastIrCommand!=POWER_CODE || timeUs-lastIrUs>=180000);
    always_ff @(posedge CLOCK_50)begin
      if(reset50)begin irSeen<=0;lastIrCommand<=0;lastIrUs<=0;end
      else if(nec_valid || nec_repeat)begin
        irSeen<=1;lastIrUs<=timeUs;
        if(nec_valid)lastIrCommand<=nec_code[23:16];
      end
    end
    wire estop_frame = nec_valid && (nec_code[23:16] == ESTOP_CODE);
    sonar_guard sonar_u(.clk50(CLOCK_50),.reset(reset50),.echo(SONAR_ECHO),
      .trig(SONAR_TRIG),.distance_mm(distance_mm),.distance_valid(distance_valid),.sample_pulse(sample_pulse));
    wire running, used, estop, sonar_stop;
    wire [2:0] stop_reason;
    (* async_reg = "true" *) logic [5:0] sw_meta, sw_sync;
    always_ff @(posedge CLOCK_50) begin
      if(reset50) begin sw_meta<=0;sw_sync<=0;end
      else begin sw_meta<=SW;sw_sync<=sw_meta;end
    end
    wire [3:0] motionState;
    wire chassis_busy,zeroSent,chassisInitSent;
    wire motionTargetValid;
    wire [511:0] controlStatusWords;
    wire signed [6:0] logicalL,logicalR;
    member_c_control #(.ULTRASONIC_ESTOP_MM(ULTRASONIC_ESTOP_MM),.TURN_SIGN(TURN_SIGN),
      .RUNTIME_TUNING(RUNTIME_TUNING),.RUNTIME_MOTION_POLICY(RUNTIME_MOTION_POLICY),
      .ALLOW_BOUNDED_ALIGN_GAP(ALLOW_BOUNDED_ALIGN_GAP),.REQUIRE_CHASSIS_INIT(INIT_FLOWOFF),
      .SELECTION_STABLE_CLKS(SELECTION_STABLE_CLKS),.ACQUIRE_SETTLE_US(ACQUIRE_SETTLE_US),
      .ACQUIRE_TIMEOUT_US(ACQUIRE_TIMEOUT_US)) control_u(
      .clk(CLOCK_50),.reset(reset50),.power_frame(power_frame),.estop_frame(estop_frame),
      .cameraFifoFault(cameraFifoFault),.cameraAbandonEvent(cameraAbandonEvent),
      .selection(sw_sync),.timeUs(timeUs),.status(perceptionStatus),.tuningWord(tuningWord),.alignTimingWord(alignTimingWord),.motionPolicyWord(motionPolicyWord),
      .mode(mode),.visualStart(visualStart),.debugStart(debugStart),.debugStop(debugStop),.modeChanged(modeChanged),
      .rawMode(rawMode),.injectLeaseValid(injectLeaseValid),.scanCalibrated(scanCalibrated),.scanBudgetUs(scanBudgetUs),
      .distanceSample(sample_pulse),.chassisInitSent(chassisInitSent),.zeroSent(zeroSent),.uartBusy(chassis_busy),.statusWords(controlStatusWords),
      .targetRequest(targetRequest),.targetRequestValid(targetRequestValid),.targetRequestReady(targetRequestReady),
      .targetReport(targetReport),.targetReportValid(targetReportValid),.targetReportReady(targetReportReady),
      .distance_valid(distance_valid),.distance_mm(distance_mm),.left_cm_s(logicalL),.right_cm_s(logicalR),
      .permit(running),.used(used),.estop(estop),.sonar_stop(sonar_stop),.motionTargetValid(motionTargetValid),
      .motionState(motionState),.stop_reason(stop_reason));
    wire signed [6:0] motorL=LEFT_POLARITY==-1 ? -logicalL : LEFT_POLARITY==1 ? logicalL:7'sd0;
    wire signed [6:0] motorR=RIGHT_POLARITY==-1 ? -logicalR : RIGHT_POLARITY==1 ? logicalR:7'sd0;
    // UART resets only at configuration, so KEY0 cannot truncate a JSON line.
    logic [1:0] uart_por = 2'b11;
    always_ff @(posedge CLOCK_50) uart_por <= {uart_por[0], 1'b0};
    // taskActive is word0 bit20; permit alone also becomes zero during an armed
    // acquisition/HOLD. Initialize only in true idle INTEGRATED/VISION_ONLY.
    wire chassisInitAllowed=!reset50 && !controlStatusWords[20] && !running &&
      logicalL==0 && logicalR==0 && mode<=1;
    // Legacy ir_drive manual control is NOT instantiated.
    chassis_command #(.CLKS_PER_BIT(434), .PERIOD_CLKS(HEARTBEAT_CLKS),
        .USE_WHEEL_REQUESTS(1),.INIT_FLOWOFF(INIT_FLOWOFF)) chassis_u (
        .clk(CLOCK_50), .reset(uart_por[1]), .armed(running && !reset50),
        .motion(2'b00), .speed(2'b00), .left_cm_s(motorL), .right_cm_s(motorR), .feedback(1'b0),
        .initAllowed(chassisInitAllowed),.softReset(reset50),.initSent(chassisInitSent),
        .tx(CHASSIS_TX), .busy(chassis_busy),.zeroSent(zeroSent));

    wire [7:0] chassis_rx_byte;
    wire chassis_rx_valid, chassis_rx_fe;
    uart_rx #(.CLKS_PER_BIT(434), .BITS_N(8), .PARITY_TYPE(0)) chassis_rx_u (
        .clk(CLOCK_50), .rst(reset50), .rx(CHASSIS_RX),
        .data_rx(chassis_rx_byte), .valid(chassis_rx_valid), .ready(1'b1),
        .parity_error(), .framing_error(chassis_rx_fe));

    logic [15:0] chassisRxCount;
    logic [7:0] lastRxByte;
    always_ff @(posedge CLOCK_50)begin
      if(reset50)begin chassisRxCount<=0;lastRxByte<=0;end
      else if(chassis_rx_valid && !chassis_rx_fe)begin chassisRxCount<=chassisRxCount+16'd1;lastRxByte<=chassis_rx_byte;end
    end
    always_comb begin
      statusWords=controlStatusWords;
      statusWords[10*32+7]=INIT_FLOWOFF;
      statusWords[10*32+8]=INIT_FLOWOFF && chassisInitSent; // local LF completion, not ESP ACK
      statusWords[12*32+:32]={7'd0,chassis_rx_fe,lastRxByte,chassisRxCount};
    end
    wire valid_led, repeat_led, rx_led;
    pulse_stretch #(.CLKS(BLINK_CLKS)) valid_blink (
        .clk(CLOCK_50), .reset(reset50), .trigger(nec_valid), .q(valid_led));
    pulse_stretch #(.CLKS(BLINK_CLKS)) repeat_blink (
        .clk(CLOCK_50), .reset(reset50), .trigger(nec_repeat), .q(repeat_led));
    pulse_stretch #(.CLKS(BLINK_CLKS)) rx_blink (
        .clk(CLOCK_50), .reset(reset50),
        .trigger(chassis_rx_valid && !chassis_rx_fe), .q(rx_led));

    // LED0 motion permit, 1 IR stop, 2 sonar valid, 3 DOCKED, 4 sonar fault; 8 target valid.
    assign LEDR = {!used && distance_valid && !reset50, motionTargetValid, repeat_led, valid_led,
      chassis_busy, (stop_reason==2), (motionState==4), distance_valid, estop, running};
endmodule
