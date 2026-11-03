`timescale 1ns/1ps
module memberBDebug_tb;
    logic clk=0;
    always #10 clk=~clk;
    logic reset=1;
    logic [perception_pkg::DEBUG_WORD_COUNT*32-1:0] debugWords;
    logic commandValid,commandReady=0,commandClear;
    logic [3:0] commandBayId;
    logic calibrateArm,speechArm,autoCycle;
    logic interactionArmReady=1;
    logic [1:0] orientationProfile;
    integer calPulses=0,speechPulses=0,commandTransfers=0;
    logic hostToggle=0;
    memberBDebug #(.BUILD_ID(32'h12345678)) dut(.*);
    always @(posedge clk) if(!reset)begin
        if(calibrateArm)calPulses=calPulses+1;
        if(speechArm)speechPulses=speechPulses+1;
        if(commandValid && commandReady)commandTransfers=commandTransfers+1;
    end
    task automatic waitClocks(input integer clocks);
        repeat(clocks)@(negedge clk);
    endtask
    task automatic issue(input logic [3:0] opcode,input logic [3:0] value);
        begin
            hostToggle=!hostToggle;
            dut.probes.src_jtag={hostToggle,3'd0,opcode,20'd0,value};
        end
    endtask
    task automatic waitAck;
        integer timeoutCount;
        begin
            timeoutCount=0;
            while(dut.probeWord[47]!==hostToggle && timeoutCount<100)begin
                @(negedge clk);timeoutCount=timeoutCount+1;
            end
            if(dut.probeWord[47]!==hostToggle)$fatal(1,"Command acknowledgement timeout");
        end
    endtask
    initial begin
        debugWords=0;
        for(int i=0;i<perception_pkg::DEBUG_WORD_COUNT;i++)debugWords[i*32+:32]=32'h10000000+i;
        waitClocks(4);reset=0;waitClocks(8);
        if(dut.probeWord[127:64]!==64'h4244424712345678 || dut.probeWord[63:48]!=={8'(perception_pkg::DEBUG_SCHEMA_VERSION),8'd2} || dut.probeWord[39:32]!==8'(perception_pkg::DEBUG_WORD_COUNT))
            $fatal(1,"BDBG/build/schema header mismatch");
        // A transient entire source word must not be accepted.
        dut.probes.src_jtag=32'h81000003;waitClocks(1);
        dut.probes.src_jtag=0;waitClocks(8);
        if(commandValid || dut.ackToggle)$fatal(1,"Unstable source accepted");
        issue(1,3);waitClocks(8);
        if(!commandValid || commandClear || commandBayId!=3 || dut.ackToggle)
            $fatal(1,"SELECT payload/early ack");
        waitClocks(7);
        if(!commandValid || commandBayId!=3 || dut.ackToggle)$fatal(1,"Stalled command changed");
        commandReady=1;waitAck();waitClocks(2);commandReady=0;
        if(commandTransfers!=1 || commandValid)$fatal(1,"SELECT duplicate transfer");
        issue(2,15);waitClocks(8);
        if(!commandValid || !commandClear || !dut.ackToggle)$fatal(1,"CLEAR lost or acknowledged before ready");
        commandReady=1;waitAck();waitClocks(2);commandReady=0;
        if(commandTransfers!=2)$fatal(1,"CLEAR transfer count");
        issue(3,0);waitAck();waitClocks(5);
        if(calPulses!=1)$fatal(1,"Calibration arm is not one pulse");
        issue(4,0);waitAck();waitClocks(5);
        if(speechPulses!=1)$fatal(1,"Speech arm is not one pulse");
        interactionArmReady=0;
        issue(3,0);waitAck();waitClocks(5);
        if(!dut.commandError||dut.rejectionReason!=2||calPulses!=2)
            $fatal(1,"Busy calibration must return action rejection once");
        interactionArmReady=1;
        issue(5,0);waitAck();waitClocks(2);
        debugWords='1;
        for(int index=0;index<perception_pkg::DEBUG_WORD_COUNT;index++)begin
            dut.probes.src_jtag={hostToggle,3'd0,4'd5,8'd0,8'(index),8'd0};
            waitClocks(8);
            if(dut.probeWord[31:0]!==32'h10000000+index)$fatal(1,"Frozen word changed/index mismatch %0d",index);
        end
        dut.probes.src_jtag={hostToggle,3'd0,4'd5,8'd0,8'd255,8'd0};waitClocks(8);
        if(dut.probeWord[31:0]!==0)$fatal(1,"Out-of-range address leaked data");
        issue(6,2);waitAck();waitClocks(2);
        if(orientationProfile!=2)$fatal(1,"Orientation command failed");
        issue(7,1);waitAck();waitClocks(2);
        if(!autoCycle)$fatal(1,"Auto cycle command failed");
        issue(1,9);waitAck();waitClocks(2);
        if(commandValid || !dut.probeWord[46])$fatal(1,"Invalid bay was accepted");
        issue(5,0);waitAck();waitClocks(2);
        if(dut.probeWord[46] || dut.probeWord[31:0]!==32'hffffffff)$fatal(1,"Refresh/error clear failed");
        // A stable old toggle remains in ISSP across reset; do not replay it.
        reset=1;waitClocks(3);reset=0;waitClocks(10);
        if(commandValid || autoCycle || orientationProfile!=0 || calibrateArm || speechArm || dut.frozenWords!='0)
            $fatal(1,"Reset replayed an old JTAG command");
        $display("PASS memberBDebug_tb: coherent commands, backpressure, %0d frozen words, reset",perception_pkg::DEBUG_WORD_COUNT);
        $finish;
    end
    initial begin #1000000;$fatal(1,"Global timeout");end
endmodule
