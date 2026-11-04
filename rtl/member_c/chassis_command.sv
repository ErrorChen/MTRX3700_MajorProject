`timescale 1ns/1ps
/*
 *  chassis_command.sv -- the UGV02 heartbeat: one JSON motion command every PERIOD_CLKS.
 *
 *  The Waveshare UGV02 listens on its 40-pin header UART at 115200 8N1 for one JSON object per
 *  line. Speed control is {"T":1,"L":<m/s>,"R":<m/s>} with L and R in -0.5 .. 0.5 (wiki: "JSON
 *  command set"), and the chassis stops by itself when no motion command has arrived for 3 s
 *  (its heartbeat). So this module sends a command every PERIOD_CLKS (200 ms on the board):
 *
 *      armed = 0            {"T":1,"L":0.00,"R":0.00}      a stop, every period: the wheels never move
 *      armed = 1            L and R from `motion` and `speed`:
 *          motion 00 forward   L = +s  R = +s          speed 00 s = SPEED0_CM_S / 100 m/s
 *                 01 backward  L = -s  R = -s                01     disabled
 *                 10 spin left L = -s  R = +s                10     disabled
 *                 11 spin right L = +s R = -s                11     disabled
 *      feedback = 1         also {"T":130} after each motion command: the chassis answers with
 *                           one line of telemetry, which is how the RX direction gets tested.
 *
 *  The text is assembled from string literals (a string literal is a packed vector of 8-bit
 *  characters in SystemVerilog), left-aligned in a MAXLEN-byte shift register, and shifted out one
 *  byte per uart_tx handshake. Nothing here is specific to the strings: change the ROM pieces and
 *  it sends something else.
 */
module chassis_command #(
    parameter int CLKS_PER_BIT = 434,           // 50 MHz / 115200
    parameter int PERIOD_CLKS  = 10_000_000,    // 200 ms at 50 MHz
    parameter bit USE_WHEEL_REQUESTS = 0,
    parameter bit INIT_FLOWOFF = 0, // optional one-shot RAM telemetry configuration
    parameter int SPEED0_CM_S  = 10             // slot 00; supplied by Top-Level
) (
    input  logic       clk,
    input  logic       reset,
    input  logic       armed,       // 0: every message is a stop
    input  logic [1:0] motion,      // 00 forward, 01 backward, 10 spin left, 11 spin right
    input  logic [1:0] speed,       // 00 parameter speed; other slots disabled in this safety test
    input logic signed [6:0] left_cm_s, right_cm_s,
    input  logic       feedback,    // 1: also ask for telemetry ({"T":130}) every period
    // initAllowed must mean truly disarmed, final zero wheels, and an allowed mode.
    // softReset only requests a fresh zero/config sequence; it never resets UART.
    input logic initAllowed, softReset,
    output logic initSent = !INIT_FLOWOFF, // local complete LF, NOT a chassis ACK
    output logic       tx,          // to the chassis RX
    output logic       busy,        // a message is going out
    output logic       zeroSent = 0 // completed zero-speed JSON, not physical rest
);
    localparam int MAXLEN = 28;
    // Constant-folded ASCII conversion: no runtime divider or DSP needed.
    // Out-of-range settings produce zero rather than a malformed speed.
    localparam int SAFE_SPEED0 = (SPEED0_CM_S >= 3 && SPEED0_CM_S <= 15) ? SPEED0_CM_S : 0;
    localparam logic [7:0] SPEED0_TENS = 8'd48 + 8'(SAFE_SPEED0 / 10);
    localparam logic [7:0] SPEED0_ONES = 8'd48 + 8'(SAFE_SPEED0 % 10);
    localparam logic [8*11-1:0] P1 = "{\"T\":1,\"L\":";
    localparam logic [8*5-1:0]  P2 = ",\"R\":";
    localparam logic [8*2-1:0]  P3 = "}\n";
    localparam logic [8*10-1:0] FB = "{\"T\":130}\n";

    localparam logic [8*18-1:0] FLOWOFF = "{\"T\":131,\"cmd\":0}\n";

    // {length, text left-aligned in MAXLEN bytes}
    function automatic logic [MAXLEN*8+7:0] motion_msg(input logic armed_i, input logic [1:0] motion_i, input logic [1:0] speed_i);
        logic [15:0] d; // Two decimal places, including the leading zero in 0.05.
        logic ln, rn;
        logic [MAXLEN*8-1:0] t;
        case (speed_i)
            2'd0:    d = {SPEED0_TENS, SPEED0_ONES};
            2'd1:    d = "00";
            2'd2:    d = "00";
            default: d = "00";
        endcase
        ln = 1'b0; rn = 1'b0;
        if (!armed_i) d = "00";
        else case (motion_i)
            2'd1:    begin ln = 1'b1; rn = 1'b1; end
            2'd2:    begin ln = 1'b1; rn = 1'b0; end
            2'd3:    begin ln = 1'b0; rn = 1'b1; end
            default: ;
        endcase
        t = '0;
        case ({ln, rn})
            2'b00:   begin t[MAXLEN*8-1 -: 26*8] = {P1, "0.",  d, P2, "0.",  d, P3}; return {8'd26, t}; end
            2'b11:   begin t[MAXLEN*8-1 -: 28*8] = {P1, "-0.", d, P2, "-0.", d, P3}; return {8'd28, t}; end
            2'b10:   begin t[MAXLEN*8-1 -: 27*8] = {P1, "-0.", d, P2, "0.",  d, P3}; return {8'd27, t}; end
            default: begin t[MAXLEN*8-1 -: 27*8] = {P1, "0.",  d, P2, "-0.", d, P3}; return {8'd27, t}; end
        endcase
    endfunction

    // Exact signed-input lookup: removes cascaded absolute-value and decimal arithmetic.
    // {legal, nonzero_negative, two ASCII decimal digits}; every unsupported value is illegal.
    function automatic logic [17:0] wheel_ascii(input logic signed [6:0] value);
      case(value)
        -7'sd15: wheel_ascii={1'b1,1'b1,"15"};
        -7'sd14: wheel_ascii={1'b1,1'b1,"14"};
        -7'sd13: wheel_ascii={1'b1,1'b1,"13"};
        -7'sd12: wheel_ascii={1'b1,1'b1,"12"};
        -7'sd11: wheel_ascii={1'b1,1'b1,"11"};
        -7'sd10: wheel_ascii={1'b1,1'b1,"10"};
        -7'sd9: wheel_ascii={1'b1,1'b1,"09"};
        -7'sd8: wheel_ascii={1'b1,1'b1,"08"};
        -7'sd7: wheel_ascii={1'b1,1'b1,"07"};
        -7'sd6: wheel_ascii={1'b1,1'b1,"06"};
        -7'sd5: wheel_ascii={1'b1,1'b1,"05"};
        -7'sd4: wheel_ascii={1'b1,1'b1,"04"};
        -7'sd3: wheel_ascii={1'b1,1'b1,"03"};
        -7'sd2: wheel_ascii={1'b1,1'b1,"02"};
        -7'sd1: wheel_ascii={1'b1,1'b1,"01"};
        7'sd0: wheel_ascii={1'b1,1'b0,"00"};
        7'sd1: wheel_ascii={1'b1,1'b0,"01"};
        7'sd2: wheel_ascii={1'b1,1'b0,"02"};
        7'sd3: wheel_ascii={1'b1,1'b0,"03"};
        7'sd4: wheel_ascii={1'b1,1'b0,"04"};
        7'sd5: wheel_ascii={1'b1,1'b0,"05"};
        7'sd6: wheel_ascii={1'b1,1'b0,"06"};
        7'sd7: wheel_ascii={1'b1,1'b0,"07"};
        7'sd8: wheel_ascii={1'b1,1'b0,"08"};
        7'sd9: wheel_ascii={1'b1,1'b0,"09"};
        7'sd10: wheel_ascii={1'b1,1'b0,"10"};
        7'sd11: wheel_ascii={1'b1,1'b0,"11"};
        7'sd12: wheel_ascii={1'b1,1'b0,"12"};
        7'sd13: wheel_ascii={1'b1,1'b0,"13"};
        7'sd14: wheel_ascii={1'b1,1'b0,"14"};
        7'sd15: wheel_ascii={1'b1,1'b0,"15"};
        default: wheel_ascii={1'b0,1'b0,"00"};
      endcase
    endfunction

    // Independent signed cm/s requests; paired invalid-input fail-closed behavior is unchanged.
    function automatic logic [MAXLEN*8+7:0] wheel_msg(input logic enable,
      input logic signed [6:0] l, r);
      logic [17:0] lc,rc;
      logic [15:0] ld,rd;
      logic ln,rn;
      logic [MAXLEN*8-1:0] t;
      begin
        lc=wheel_ascii(l);rc=wheel_ascii(r);
        if(enable && lc[17] && rc[17])begin
          ld=lc[15:0];rd=rc[15:0];ln=lc[16];rn=rc[16];
        end else begin ld="00";rd="00";ln=0;rn=0;end
        t='0;
        case({ln,rn})
          2'b00:begin t[MAXLEN*8-1 -: 26*8]={P1,"0.",ld,P2,"0.",rd,P3};return {8'd26,t};end
          2'b11:begin t[MAXLEN*8-1 -: 28*8]={P1,"-0.",ld,P2,"-0.",rd,P3};return {8'd28,t};end
          2'b10:begin t[MAXLEN*8-1 -: 27*8]={P1,"-0.",ld,P2,"0.",rd,P3};return {8'd27,t};end
          default:begin t[MAXLEN*8-1 -: 27*8]={P1,"0.",ld,P2,"-0.",rd,P3};return {8'd27,t};end
        endcase
      end
    endfunction

    logic signed [6:0] sentL=0,sentR=0;
    wire signed [6:0] desiredL=armed?left_cm_s:7'sd0;
    wire signed [6:0] desiredR=armed?right_cm_s:7'sd0;
    wire wheelsChanged=USE_WHEEL_REQUESTS && (desiredL!=sentL || desiredR!=sentR);

    // ---- the period ----
    localparam int PW = $clog2(PERIOD_CLKS);
    logic [PW-1:0] timer = '0;
    logic tick;
    always_ff @(posedge clk)
        if (reset) timer <= '0;
        else       timer <= (timer == PW'(PERIOD_CLKS - 1)) ? '0 : timer + 1'b1;
    assign tick = (timer == PW'(PERIOD_CLKS - 1));

    // ---- the sender ----
    logic [MAXLEN*8-1:0] shreg = '0;
    logic [7:0]          remaining = '0;
    logic                fb_pending = 1'b0;
    logic                tx_valid = 1'b0, tx_ready;
    logic last_armed = 0, stop_pending = 1;
    logic messageIsZero=1,messageIsMotion=1;
    logic messageIsInit=0, initMessageCurrent=0;
    logic lastSoftReset=0, heartbeatPending=0;
    wire softResetEdge=INIT_FLOWOFF && softReset && !lastSoftReset;
    wire stop_edge = last_armed && !armed;
    wire effectiveStop=stop_pending || stop_edge || softResetEdge;
    enum logic [1:0] {IDLE, SEND, LOAD_FB} state = IDLE;

    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT), .BITS_N(8)) tx_u (
        .clk(clk), .rst(reset), .data_tx(shreg[MAXLEN*8-1 -: 8]), .valid(tx_valid), .uart_out(tx), .ready(tx_ready));

    always_ff @(posedge clk) begin
        last_armed <= armed;
        lastSoftReset <= softReset;
        if (stop_edge) stop_pending <= 1;
        // A config line may straddle the free-running wheel heartbeat tick.
        // Remember that obligation without changing the period or ordinary motion semantics.
        if (INIT_FLOWOFF && messageIsInit && state==SEND && tick) heartbeatPending<=1;
        if (reset) begin
            last_armed <= 0; stop_pending <= 1; sentL<=0;sentR<=0;
            state <= IDLE; tx_valid <= 1'b0; remaining <= '0; fb_pending <= 1'b0;
            zeroSent<=0;messageIsZero<=1;messageIsMotion<=1;
            messageIsInit<=0;initMessageCurrent<=0;lastSoftReset<=0;heartbeatPending<=0;
            initSent<=!INIT_FLOWOFF;
        end else case (state)
            IDLE: if (stop_pending || stop_edge || softResetEdge || tick || heartbeatPending || wheelsChanged || (armed && !last_armed)) begin
                heartbeatPending<=0;messageIsInit<=0;
                if(USE_WHEEL_REQUESTS)
                    {remaining,shreg}<=wheel_msg(armed && !effectiveStop,left_cm_s,right_cm_s);
                else {remaining, shreg} <= motion_msg(armed && !effectiveStop, motion, speed);
                sentL<=armed && !effectiveStop ? left_cm_s:7'sd0;
                sentR<=armed && !effectiveStop ? right_cm_s:7'sd0;
                messageIsMotion<=1;
                messageIsZero<=!armed || effectiveStop ||
                  (USE_WHEEL_REQUESTS && left_cm_s==0 && right_cm_s==0);
                if(armed && !effectiveStop &&
                  (!USE_WHEEL_REQUESTS || left_cm_s!=0 || right_cm_s!=0))zeroSent<=0;
                stop_pending <= 0;
                fb_pending <= feedback && !effectiveStop;
                state <= SEND;
            end else if(INIT_FLOWOFF && !initSent && !softReset && initAllowed &&
                        !armed && desiredL==0 && desiredR==0 && zeroSent && tx_ready) begin
                // One shared serializer, after a complete stop. Configuration never
                // impersonates a motion packet or changes the sent wheel baseline.
                shreg<={FLOWOFF,{(MAXLEN-18)*8{1'b0}}};remaining<=18;
                messageIsMotion<=0;messageIsInit<=1;initMessageCurrent<=1;
                fb_pending<=0;state<=SEND;
            end
            SEND: begin
                if (!tx_valid) begin
                    if (remaining == 0 && tx_ready) begin
                        state <= (fb_pending && !effectiveStop) ? LOAD_FB : IDLE;
                        if(messageIsMotion && messageIsZero)zeroSent<=1;
                        if(INIT_FLOWOFF && messageIsInit && initMessageCurrent && !softReset) initSent<=1;
                    end
                    else if (tx_ready)   tx_valid <= 1'b1;
                end else if (tx_ready) begin              // handshake: this byte is taken
                    tx_valid  <= 1'b0;
                    shreg     <= shreg << 8;
                    remaining <= remaining - 1'b1;
                end
            end
            LOAD_FB: if(effectiveStop) begin
                fb_pending<=0;state<=IDLE;
            end else begin
                messageIsMotion<=0;messageIsInit<=0;
                shreg <= {FB, {(MAXLEN - 10) * 8{1'b0}}};
                remaining <= 8'd10;
                fb_pending <= 1'b0;
                state <= SEND;
            end
            default: state <= IDLE;
        endcase
        // Highest-priority bookkeeping only: leave state/shifter/UART intact.
        // A reset during an old config invalidates that completion and queues
        // an entirely new zero -> config transaction after reset is released.
        if(!reset && softResetEdge) begin
            initSent<=0;initMessageCurrent<=0;stop_pending<=1;zeroSent<=0;
        end
    end
    assign busy = (state != IDLE);
endmodule
