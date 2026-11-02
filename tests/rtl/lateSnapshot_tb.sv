`timescale 1ns/1ps
// Real frame_snap control/RAM/CRC path, using the existing simulation-only RAM
// primitive. Late result acceptance is explicitly independent of later pixels.
module lateSnapshot_tb;
    logic clk=0;always #25 clk=~clk;
    logic reset=1,frameStart=0,valid=0,trigger=0,resultValid=0;
    logic [15:0] pixel=16'h1234;
    logic [9:0] x=0;
    logic [8:0] y=0;
    logic [31:0] results=32'h45425031;
    wire busy,ready,resultTimeout;
    wire [15:0] capturedId;
    frame_snap #(.MODE(1),.N_RESULTS(1),.WAIT_FOR_RESULTS(1),.RESULT_TIMEOUT_CYCLES(500)) dut (
        .pclk(clk),.reset(reset),.frame_start(frameStart),.px_valid(valid),.pixel(pixel),.x(x),.y(y),
        .results(results),.trigger(trigger),.busy(busy),.ready(ready),.results_valid(resultValid),
        .captured_frame_id(capturedId),.result_timeout(resultTimeout));
    task automatic tick;@(posedge clk);#1;endtask
    task automatic startFrame;
        @(negedge clk);frameStart=1;tick();@(negedge clk);frameStart=0;tick();
    endtask
    task automatic request;
        @(negedge clk);trigger=1;repeat(5)tick();@(negedge clk);trigger=0;repeat(5)tick();
    endtask
    task automatic capturePixels;
        for(int yy=0;yy<120;yy++)for(int xx=0;xx<160;xx++)begin
            @(negedge clk);valid=1;x=10'(xx*4);y=9'(yy*4);tick();
        end
        @(negedge clk);valid=0;tick();
    endtask
    initial begin
        repeat(4)tick();@(negedge clk);reset=0;repeat(4)tick();
        request();startFrame();capturePixels();startFrame();
        assert(capturedId==1&&!ready&&busy)else $fatal(1,"capture ownership/id");
        // Pixels in a newer frame cannot trigger copying of an unrelated result.
        repeat(30)begin @(negedge clk);valid=1;tick();end
        @(negedge clk);valid=0;results=32'hcafef00d;resultValid=1;tick();
        @(negedge clk);resultValid=0;
        repeat(40000)tick();
        assert(ready&&!busy&&!resultTimeout)else $fatal(1,"late matching result not published");
        assert(dut.results_q==32'hcafef00d)else $fatal(1,"wrong result latched");
        assert(dut.ram_u.mem[7]==16'hcafe&&dut.ram_u.mem[8]==16'hf00d)else $fatal(1,"header result ordering");
        assert(dut.ram_u.mem[9]==16'h1234)else $fatal(1,"held frame overwritten");
        request();startFrame();capturePixels();startFrame();repeat(550)tick();
        assert(resultTimeout&&!ready&&!busy)else $fatal(1,"missing result must fail without stale ready");
        request();startFrame();capturePixels();startFrame();
        @(negedge clk);resultValid=1;tick();@(negedge clk);resultValid=0;repeat(40000)tick();
        assert(ready&&!resultTimeout)else $fatal(1,"snapshot timeout not recoverable");
        $display("PASS lateSnapshot_tb late-results same-frame RAM ownership timeout recovery");$finish;
    end
    initial begin #20000000;$fatal(1,"test timeout");end
endmodule
