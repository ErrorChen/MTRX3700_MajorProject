// Member B bench: native camera, HSV/projective perception, a safe C simulator,
// JTAG evidence and live VGA. Chassis pins remain undriven. The inherited camera
// configuration/capture/display path retains its original attribution.
// AI-assisted implementation: OpenAI Codex; see docs/inputs/OWNERS.md and docs/inputs/AI_STATEMENT.md.
/*
 *  perceptionDemoTop.sv -- OV7670 camera and Member B on the DE1-SoC.
 *
 *      CLOCK_50 --> video_pll --> clk_25 (display, SCCB /250) and clk_10 --> camera XCLK (GPIO_1[20]); sensor x4 PLL then /2 prescaler = 20 MHz PCLK at 25 fps.
 *                                   |
 *      clock_divider --> 100 kHz --> ov7670_config --SCCB--> camera (RESET#, PWDN, SIO_C, SIO_D)
 *
 *      camera PCLK/VSYNC/HREF/D --> ov7670_capture --> frame_buffer (write port, PCLK domain)
 *                                                        frame_buffer (read port, clk_25 domain)
 *                                                            --> camera_display --> marker overlay --> vga_sink --> VGA
 *      kept pixels --> asynchronous FIFO --> CLOCK_50 perceptionCore --> C simulator / JTAG
 *
 *  Pins: the Robot Adaptor Board puts the camera on GPIO_1[10..25]; the stock DE1-SoC pin
 *  assignments are used, and the mapping lives here, in one place:
 *      PWDN 10, RESET# 11, D0..D7 12..19, XCLK 20, PCLK 21, HREF 22, VSYNC 23, SIO_D 24, SIO_C 25.
 *
 *  Controls: KEY0 = reset (re-runs the camera configuration). LEDR0 = camera configured,
 *  LEDR1 = the last SCCB write got no acknowledge (being retried: check the loom and XCLK),
 *  LEDR2 toggles once per camera frame (12.5 Hz at the required 25 fps).
 */
`include "memberBBuildId.svh"
module perceptionDemoTop #(
    parameter int CAMERA_FPS = 25 // Physical camera configuration and 20 MHz PCLK constraint.
) (
    input  wire        CLOCK_50,
    output wire [6:0] HEX0, HEX1, HEX2,
    input  wire [3:0]  KEY,
    input  wire [4:0]  SW, // Reserved board inputs; debug control is versioned JTAG.
    output wire [9:0]  LEDR,
    inout  wire [35:0] GPIO_1,
    output wire        VGA_CLK, VGA_HS, VGA_VS, VGA_BLANK_N, VGA_SYNC_N,
    output wire [7:0]  VGA_R, VGA_G, VGA_B
);
    // Match the physical sensor clock to PartBDebug.sdc. This undefined-module
    // elaboration guard also applies in synthesis (same pattern as ov7670_config).
    generate if (CAMERA_FPS != 25) begin : requires_25fps
        MemberB_requires_CAMERA_FPS_25_and_20MHz_PCLK stop_here ();
    end endgenerate
    // ---- clocks ------------------------------------------------------------------------------
    wire clk_25, pll_locked;
    wire clk_10;
    video_pll video_pll_u (.refclk(CLOCK_50), .rst(1'b0), .outclk_0(clk_25), .outclk_1(clk_10), .locked(pll_locked));
    wire sccb_clk;
    clock_divider #(.DIVISOR(250)) sccb_clk_u (.clk_in(clk_25), .clk_out(sccb_clk));   // 100 kHz

    // ---- reset: KEY0 (active low), synchronised into each domain ---------------------------------
    logic [1:0] rs25 = '1, rs_sccb = '1;
    always_ff @(posedge clk_25)   rs25    <= {rs25[0],    ~KEY[0] | ~pll_locked};
    always_ff @(posedge sccb_clk) rs_sccb <= {rs_sccb[0], ~KEY[0]};
    wire reset25 = rs25[1], reset_sccb = rs_sccb[1];

    // ---- the camera's pins ---------------------------------------------------------------------
    wire       cam_pclk  = GPIO_1[21];
    wire       cam_href  = GPIO_1[22];
    wire       cam_vsync = GPIO_1[23];
    wire [7:0] cam_d     = GPIO_1[19:12];
    wire       cam_reset_n, cam_pwdn, sioc;
    assign GPIO_1[20] = clk_10;          // XCLK10 MHz; sensor PLLx4 and CLKRC0x81 /2 produce20 MHz PCLK.
    assign GPIO_1[11] = cam_reset_n;     // RESET#
    assign GPIO_1[10] = cam_pwdn;        // PWDN
    assign GPIO_1[25] = sioc;            // SIO_C
    // GPIO_1[24] is SIO_D, driven open-drain from inside ov7670_config; every other pin stays an input

    // ---- configure the camera ------------------------------------------------------------------
    wire cfg_done, cfg_error;
    ov7670_config #(.FPS(CAMERA_FPS)) cfg_u (
        .clk(sccb_clk), .reset(reset_sccb), .sioc(sioc), .siod(GPIO_1[24]),
        .cam_reset_n(cam_reset_n), .cam_pwdn(cam_pwdn), .done(cfg_done), .error(cfg_error));

    // ---- capture the stream (PCLK domain) --------------------------------------------------------
    wire        frame_start, px_valid;
    wire [15:0] px;
    wire [9:0]  px_x;
    wire [8:0]  px_y;
    ov7670_capture cap_u (
        .pclk(cam_pclk), .vsync(cam_vsync), .href(cam_href), .d(cam_d),
        .frame_start(frame_start), .valid(px_valid), .pixel(px), .x(px_x), .y(px_y));

    // ---- one picture in memory: written at PCLK, read at clk_25 ----------------------------------
    wire [8:0]  rd_x;
    wire [7:0]  rd_y;
    wire [15:0] rd_pixel;
    frame_buffer #(.W(320), .H(240), .DW(16), .DECIMATE(2), .BUFFERS(1), .PACKED(0)) fb_u (   // one 16-bit picture, 150 M10K: simple; a moving scene can tear (frame_buffer.sv has 2 / 3 banks and packing)
        .wr_clk(cam_pclk), .wr_frame_start(frame_start), .wr_valid(px_valid), .wr_x(px_x), .wr_y(px_y), .wr_pixel(px),
        .rd_clk(clk_25), .rd_x(rd_x), .rd_y(rd_y), .rd_pixel(rd_pixel));

    // ---- show it -----------------------------------------------------------------------------------
    wire [29:0] st_data;
    wire        st_sop, st_eop, st_valid, st_ready;
    camera_display #(.H_RES(640), .V_RES(480), .W(320), .H(240), .ROTATE_CCW_90(1)) disp_u (
        .clk(clk_25), .reset(reset25), .hold_enable(1'b1), .rd_x(rd_x), .rd_y(rd_y), .rd_pixel(rd_pixel),
        .data(st_data), .startofpacket(st_sop), .endofpacket(st_eop), .valid(st_valid), .ready(st_ready));


    import perception_pkg::*;
    logic [1:0] rs50='1,rsPclk='1;
    always_ff @(posedge CLOCK_50) rs50<={rs50[0],~KEY[0]};
    always_ff @(posedge cam_pclk) rsPclk<={rsPclk[0],~KEY[0]};
    wire reset50=rs50[1],resetPclk=rsPclk[1];
    logic [5:0] microsecondDivider;
    logic [31:0] timeUs;
    always_ff @(posedge CLOCK_50) begin
        if(reset50) begin microsecondDivider<=0;timeUs<=0;end
        else if(microsecondDivider==49)begin microsecondDivider<=0;timeUs<=timeUs+32'd1;end
        else microsecondDivider<=microsecondDivider+6'd1;
    end
    targetRequest_t targetRequest,currentRequest;
    targetReport_t targetReport,cachedReport;
    userEvent_t userEvent;
    perceptionStatus_t status;
    logic requestValid,requestReady,reportValid,reportReady,eventValid,eventReady;
    logic commandValid,commandReady,commandClear,calibrateArm,speechArm,autoCycle,measurementUsable;
    logic [3:0] commandBayId;
    logic [1:0] orientationProfile;
    logic [3071:0] coreWords,debugWords,completedWords,cameraWords,displayWords;
    logic completedFrame;
    logic [15:0] completedFrameId;
    always_comb begin
        debugWords=coreWords;
        debugWords[92*32+:32]=`MEMBER_B_BUILD_ID;
    end
    perceptionCore core (
        .clk(CLOCK_50),.reset(reset50),.pclk(cam_pclk),.resetPclk(resetPclk),
        .cameraFrameStart(frame_start),.cameraPixelValid(px_valid),.cameraPixel(px),.cameraX(px_x),.cameraY(px_y),
        .timeUs(timeUs),.interactionEnable(1'b1),.interactionPermit(1'b1),
        .debugCalArm(calibrateArm),.debugSpeechArm(speechArm),.orientationProfile(orientationProfile),
        .targetRequest(targetRequest),.targetRequestValid(requestValid),.targetRequestReady(requestReady),
        .targetReport(targetReport),.targetReportValid(reportValid),.targetReportReady(reportReady),
        .userEvent(userEvent),.userEventValid(eventValid),.userEventReady(eventReady),.status(status),
        .debugWords(coreWords),.completedFrame(completedFrame),.completedFrameId(completedFrameId));
    memberCSimulator cModel (
        .clk(CLOCK_50),.reset(reset50),.timeUs(timeUs),.commandValid(commandValid),.commandReady(commandReady),
        .commandClear(commandClear),.commandBayId(commandBayId),.autoCycle(autoCycle),
        .interactionEnable(1'b1),.interactionPermit(1'b1),.status(status),
        .targetRequest(targetRequest),.targetRequestValid(requestValid),.targetRequestReady(requestReady),
        .targetReport(targetReport),.targetReportValid(reportValid),.targetReportReady(reportReady),
        .userEvent(userEvent),.userEventValid(eventValid),.userEventReady(eventReady),
        .cachedReport(cachedReport),.measurementUsable(measurementUsable),.currentRequest(currentRequest),
        .acceptedEventPulse(),.rejectedEventPulse());
    memberBDebug #(.BUILD_ID(`MEMBER_B_BUILD_ID)) debugControl (
        .clk(CLOCK_50),.reset(reset50),.debugWords(debugWords),.commandValid(commandValid),.commandReady(commandReady),
        .commandClear(commandClear),.commandBayId(commandBayId),.calibrateArm(calibrateArm),.speechArm(speechArm),
        .orientationProfile(orientationProfile),.autoCycle(autoCycle));
    // Wait until the tracker has consumed the completed observation. Freeze a
    // complete frame record, then cross it with a held-bus request/ack handshake.
    logic [1:0] completionDelay;
    always_ff @(posedge CLOCK_50)begin
        if(reset50)begin completionDelay<=0;completedWords<=0;end
        else begin
            completionDelay<={completionDelay[0],completedFrame};
            if(completionDelay[1])completedWords<=debugWords;
        end
    end
    heldBusCdc #(.WIDTH(3072)) resultToCamera (
        .sourceClk(CLOCK_50),.sourceReset(reset50),.sourceData(completedWords),
        .destinationClk(cam_pclk),.destinationReset(resetPclk),.destinationData(cameraWords),.destinationValid());
    heldBusCdc #(.WIDTH(3072)) resultToDisplay (
        .sourceClk(CLOCK_50),.sourceReset(reset50),.sourceData(completedWords),
        .destinationClk(clk_25),.destinationReset(reset25),.destinationData(displayWords),.destinationValid());
    logic [29:0] overlayData;
    logic overlaySop,overlayEop,overlayValid,overlayReady;
    memberBVgaOverlay overlay (
        .clk(clk_25),.reset(reset25),.debugWords(displayWords),
        .inData(st_data),.inSop(st_sop),.inEop(st_eop),.inValid(st_valid),.inReady(st_ready),
        .outData(overlayData),.outSop(overlaySop),.outEop(overlayEop),.outValid(overlayValid),.outReady(overlayReady));
    vga_sink vga_u (
        .clk_clk(clk_25),.reset_reset_n(~reset25),.video_in_data(overlayData),
        .video_in_startofpacket(overlaySop),.video_in_endofpacket(overlayEop),
        .video_in_valid(overlayValid),.video_in_ready(overlayReady),
        .vga_CLK(VGA_CLK),.vga_HS(VGA_HS),.vga_VS(VGA_VS),.vga_BLANK(VGA_BLANK_N),.vga_SYNC(VGA_SYNC_N),
        .vga_R(VGA_R),.vga_G(VGA_G),.vga_B(VGA_B));
    // GRAB holds its actual captured frame while waiting for matching rectified
    // results. It never combines a new picture with the latest unrelated packet.
    logic [15:0] sensorFrameId;
    logic [15:0] snapshotFrameId;
    logic snapshotResultTimeout;
    logic [98*32-1:0] snapshotResults;
    always_ff @(posedge cam_pclk)begin
        if(resetPclk)sensorFrameId<=0;
        else if(frame_start)sensorFrameId<=sensorFrameId+16'd1;
    end
    always_comb begin
        snapshotResults='0;
        for(int i=0;i<96;i++)snapshotResults[(97-i)*32+:32]=cameraWords[i*32+:32];
        snapshotResults[32+:32]={16'd0,snapshotFrameId};
        snapshotResults[0+:32]=`MEMBER_B_BUILD_ID;
    end
    logic snapBusy,snapReady;
    frame_snap #(.MODE(0),.N_RESULTS(98),.WAIT_FOR_RESULTS(1)) snap_u (
        .pclk(cam_pclk),.reset(resetPclk),.frame_start(frame_start),.px_valid(px_valid),.pixel(px),.x(px_x),.y(px_y),
        .results(snapshotResults),.trigger(~KEY[1]),.busy(snapBusy),.ready(snapReady),
        .results_valid(cameraWords[3*32+:16]==snapshotFrameId),
        .captured_frame_id(snapshotFrameId),.result_timeout(snapshotResultTimeout));
    assign GPIO_1[9:0]=10'bz;
    assign GPIO_1[35:26]=10'bz;
    assign HEX0=7'h7f;assign HEX1=7'h7f;assign HEX2=7'h7f;
    assign LEDR={status.speechArmed,status.calibrated,measurementUsable,status.interactionBusy,
        status.perceptionReady,snapBusy,snapReady,sensorFrameId[0],cfg_error,cfg_done};
endmodule
