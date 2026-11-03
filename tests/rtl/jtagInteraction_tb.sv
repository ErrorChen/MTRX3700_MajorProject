`timescale 1ns/1ps
// Real BCTL decoder linked to the production interaction FSM. Forced state
// coverage is protocol injection, not camera recognition evidence.
module jtagInteraction_tb;
    import perception_pkg::*;
    logic clk=0,reset=1;
    always #10 clk=~clk;
    logic [perception_pkg::DEBUG_WORD_COUNT*32-1:0] debugWords=0;
    logic commandValid,commandReady=1;
    targetOperation_t commandOperation;
    markerType_t commandMarkerType;
    logic [3:0] commandDigit;
    queryResult_t queryResult='0;
    logic queryResultValid=0,queryResultReady,queryBusy=0;
    logic calibrateArm,speechArm,autoCycle;
    logic [1:0] orientationProfile;
    logic enable=1,permit=1,frameValid=0,frameGood=1,red1Paired=1,red2Seen=1;
    logic [31:0] timeUs=0;
    logic [15:0] frameId=0,configVersion=0,activeCfgVersion=0,commitVersion=0;
    logic sampleResultValid=0,sampleGood=1,commitAck=0;
    logic collectEnable,commitRequest,calibrationAttempt,calibrated,speechArmed,busy,eventOverflow;
    logic [3:0] sampleCount;
    logic [15:0] interactionId;
    interactionKind_t kind;
    interactionState_t state,forcedState;
    userEvent_t userEvent;
    logic userEventValid,userEventReady=1;
    wire interactionArmReady=enable&&(state==INTERACTION_IDLE||state==INTERACTION_SPEECH_ARMED);
    wire debugCalArm=calibrateArm&&interactionArmReady;
    wire debugSpeechArm=speechArm&&interactionArmReady;
    bit hostToggle=0;
    integer acceptedArms=0,checks=0;
    memberBDebug debugPort(.*);
    fixedSheetInteraction interaction(.*);
    always @(posedge clk)if(!reset)begin
        timeUs<=timeUs+1;
        if(debugCalArm)acceptedArms++;
    end
    task automatic command(input integer opcode,input bit expectedAccepted);
        integer cycles;
        begin
            @(negedge clk);hostToggle=!hostToggle;
            debugPort.probes.src_jtag={hostToggle,3'd0,4'(opcode),24'd0};
            cycles=0;
            while(debugPort.ackToggle!==hostToggle&&cycles<80)begin @(negedge clk);cycles++;end
            if(cycles==80)$fatal(1,"BCTL action timeout");
            if(debugPort.commandError!==!expectedAccepted||
                debugPort.rejectionReason!==(expectedAccepted?2'd0:2'd2))
                $fatal(1,"Busy action ACK incorrectly implies acceptance state=%0d",state);
            checks++;
        end
    endtask
    task automatic frame(input bit sample);
        @(negedge clk);frameId++;frameValid=1;sampleResultValid=sample;
        @(negedge clk);frameValid=0;sampleResultValid=0;
    endtask
    initial begin
        repeat(4)@(negedge clk);reset=0;repeat(8)@(negedge clk);
        command(3,1);repeat(6)@(negedge clk);
        if(acceptedArms!=1||busy)$fatal(1,"Idle rearm must accept once without inventing a card");
        repeat(10)@(negedge clk);
        if(acceptedArms!=1)$fatal(1,"Held toggle repeated action");
        // Automatic recognition can enter COLLECT while the JTAG word settles.
        // Action acceptance is checked at the actual FSM sampling edge.
        frame(0);frame(0);frame(0);
        if(state!=INTERACTION_CAL_COLLECT)$fatal(1,"Real red1 confirmation did not start");
        command(3,0);
        if(acceptedArms!=1||interactionId!=1)$fatal(1,"Busy command changed active interaction");
        for(int n=0;n<8;n++)frame(1);
        repeat(2)@(negedge clk);
        if(state!=INTERACTION_CAL_COMMIT)$fatal(1,"Eight real sample results did not request commit");
        command(3,0);
        commitVersion=1;activeCfgVersion=1;configVersion=1;commitAck=1;
        @(negedge clk);commitAck=0;repeat(6)@(negedge clk);
        if(!calibrated||busy)$fatal(1,"Busy command disturbed committed result");
        for(int code=1;code<=7;code++)begin
            if(code==5||code==6)continue;
            forcedState=interactionState_t'(code);
            force interaction.state=forcedState;
            command(3,0);command(4,0);
            release interaction.state;
        end
        force interaction.state=INTERACTION_SPEECH_ARMED;
        command(3,1);
        enable=0;command(3,0);enable=1;
        release interaction.state;
        reset=1;repeat(4)@(negedge clk);reset=0;repeat(12)@(negedge clk);
        if(calibrateArm||speechArm||busy||interactionId!=0)
            $fatal(1,"Reset replayed retained old JTAG source");
        $display("PASS jtagInteraction_tb checks=%0d acceptedArms=%0d",checks,acceptedArms);
        $finish;
    end
    initial begin #200000;$fatal(1,"JTAG/FSM linked regression timeout");end
endmodule
