`timescale 1ns/1ps
module targetTracker_tb;
    import perception_pkg::*;
    logic clk=0, reset=1;
    always #10 clk=~clk;
    logic [31:0] timeUs=0;
    logic [15:0] activeCfgVersion=0;
    logic perceptionReady=1;
    targetRequest_t targetRequest, activeRequest;
    logic targetRequestValid=0,targetRequestReady;
    frameObservation_t frameObservation;
    logic frameValid=0;
    targetReport_t targetReport, savedReport;
    logic targetReportValid,targetReportReady=1;
    logic [15:0] reportDropCount;
    logic requestInvalidFault;
    integer nextFrame=1;
    targetTracker dut(.*);
    task automatic tick;
        @(posedge clk); #1;
    endtask
    task automatic restart;
        @(negedge clk); reset=1; frameValid=0; targetRequestValid=0; targetReportReady=1;
        tick();
        if (targetReportValid || targetRequestReady) $fatal(1,"reset handshake");
        @(negedge clk); reset=0;
        tick();
    endtask
    task automatic request(input targetOperation_t op,input integer digit,input integer tag,
                           input markerType_t markerType=MARKER_BAY);
        targetRequest_t beforeRequest;
        beforeRequest=activeRequest;
        @(negedge clk); targetRequest.operation=op; targetRequest.digit=4'(digit);
        targetRequest.markerType=markerType;
        targetRequest.requestTag=tag; targetRequestValid=1;
        tick();
        if (!targetRequestReady) $fatal(1,"request readiness");
        if (op==TARGET_LIST || op==TARGET_GET) begin
            if(activeRequest!==beforeRequest) $fatal(1,"query changed tracker identity");
        end else if(activeRequest!=targetRequest) $fatal(1,"request acceptance");
        @(negedge clk); targetRequestValid=0;
    endtask
    task automatic frame(input integer id,input integer count,input bit good);
        @(negedge clk);
        frameObservation.boundRequest=activeRequest;
        frameObservation.frameId=id;
        frameObservation.captureStartUs=id*40000;
        frameObservation.configVersion=activeCfgVersion;
        frameObservation.frameGood=good;
        frameObservation.resourceDrop=0;
        frameObservation.matchCount=count;
        frameObservation.xMin=10; frameObservation.xMax=13;
        frameObservation.yMin=20; frameObservation.yMax=24;
        frameObservation.quality=220;
        frameValid=1;
        tick();
        if (!targetReportValid) $fatal(1,"report must assert without waiting ready");
        @(negedge clk); frameValid=0;
    endtask
    task automatic checkNoMeasurement;
        if (targetReport.observed || targetReport.locked || targetReport.centreU ||
            targetReport.centreV || targetReport.boxWidth || targetReport.boxHeight || targetReport.quality)
            $fatal(1,"unobserved measurements must be zero");
    endtask
    initial begin
        targetRequest='0; frameObservation='0;
        if ($bits(targetRequest_t)!=24 || $bits(targetReport_t)!=141 || $bits(queryResult_t)!=141 ||
            $bits(userEvent_t)!=104 || $bits(perceptionStatus_t)!=76) $fatal(1,"v3 widths");
        if (DEFAULT_ACTIVE_BAY_MASK!=10'h07e || INTERACTION_SPEECH_ARMED!=9) $fatal(1,"v3 constants");
        restart();
        for (int bay=1;bay<=6;bay++) begin
            request(TARGET_SELECT,bay,bay);
            for(int n=1;n<=3;n++) begin
                frame(nextFrame,1,1); nextFrame++;
                if (!targetReport.observed || targetReport.locked!=(n==3) || targetReport.digit!=bay || targetReport.markerType!=MARKER_BAY)
                    $fatal(1,"three-frame lock bay=%0d n=%0d",bay,n);
                if(targetReport.centreU!=22 || targetReport.centreV!=307 ||
                   targetReport.boxWidth!=5 || targetReport.boxHeight!=4) $fatal(1,"bbox-before-centre rotation");
            end
        end
        // The same tracker supports red function signs and the actual paired
        // blue reference. Their match counts originate in the typed core scan.
        for(int typed=1;typed<=3;typed++) begin
            request(TARGET_SELECT,typed==3?15:typed,200+typed,
                    typed==3?MARKER_REFERENCE:MARKER_FUNCTION);
            for(int n=1;n<=3;n++) begin
                frame(nextFrame,1,1);nextFrame++;
                if(!targetReport.observed || targetReport.locked!=(n==3) ||
                   targetReport.markerType!=activeRequest.markerType || targetReport.digit!=activeRequest.digit)
                    $fatal(1,"typed red/reference tracking");
            end
        end
        request(TARGET_SELECT,1,210,MARKER_FUNCTION);
        frame(nextFrame,1,1);nextFrame++;
        frame(nextFrame,1,1);nextFrame++;
        request(TARGET_GET,1,211,MARKER_BAY);
        request(TARGET_LIST,15,212,MARKER_NONE);
        frame(nextFrame,1,1);nextFrame++;
        if(!targetReport.locked || targetReport.requestTag!=210 || requestInvalidFault)
            $fatal(1,"queries changed three-frame continuity/tag/fault");
        frame(nextFrame,0,1); nextFrame++;
        checkNoMeasurement();
        if(targetReport.reason!=REPORT_NOT_FOUND) $fatal(1,"missing reason");
        frame(nextFrame,1,1); nextFrame++;
        if(targetReport.locked) $fatal(1,"missing clears confirmation");
        frame(nextFrame,2,1); nextFrame++;
        checkNoMeasurement();
        if(!targetReport.ambiguous || targetReport.reason!=REPORT_DUPLICATE_ID) $fatal(1,"ambiguity");
        frame(nextFrame,1,0); nextFrame++;
        checkNoMeasurement();
        if(targetReport.frameGood || targetReport.reason!=REPORT_FRAME_BAD) $fatal(1,"bad frame");
        frame(nextFrame,1,1); nextFrame++;
        frame(nextFrame,1,1); nextFrame++;
        frame(nextFrame+1,1,1); nextFrame+=2;
        if(targetReport.locked) $fatal(1,"frame gap must restart lock");
        frame(nextFrame-1,1,1);
        checkNoMeasurement();
        if(targetReport.frameGood) $fatal(1,"duplicate capture rejected");
        activeCfgVersion=1;
        for(int n=1;n<=3;n++) begin
            frame(nextFrame,1,1); nextFrame++;
            if(targetReport.locked!=(n==3)) $fatal(1,"new config requires three frames");
        end
        // Preserve the original tag carried by a frame completed after a new request.
        savedReport=targetReport;
        request(TARGET_SELECT,3,100);
        @(negedge clk);
        frameObservation.boundRequest.requestTag=6; frameObservation.boundRequest.digit=6;
        frameObservation.boundRequest.markerType=MARKER_BAY;
        frameObservation.frameId=nextFrame; nextFrame++; frameValid=1;
        tick();
        if(targetReport.requestTag!=6 || targetReport.reason!=REPORT_REQUEST_CHANGED) $fatal(1,"old frame was relabelled");
        checkNoMeasurement();
        @(negedge clk); frameValid=0;
        request(TARGET_CLEAR,0,101);
        frame(nextFrame,1,1); nextFrame++;
        checkNoMeasurement();
        if(targetReport.markerType!=MARKER_NONE || targetReport.digit!=15 || targetReport.targetSelected || targetReport.reason!=REPORT_NO_SELECTION)
            $fatal(1,"CLEAR is independent from zero");
        for(int invalidBay=0;invalidBay<=9;invalidBay++) begin
            if(invalidBay==0 || invalidBay>=7) begin
                request(TARGET_SELECT,invalidBay,102+invalidBay);
                frame(nextFrame,1,1); nextFrame++;
                checkNoMeasurement();
                if(!requestInvalidFault || targetReport.reason!=REPORT_INVALID_REQUEST || targetReport.targetSelected)
                    $fatal(1,"disabled bay accepted");
            end
        end
        request(TARGET_SELECT,3,220,MARKER_FUNCTION);
        frame(nextFrame,1,1);nextFrame++;
        if(targetReport.reason!=REPORT_INVALID_REQUEST || targetReport.markerType!=MARKER_NONE)
            $fatal(1,"unsupported red function digit accepted");
        request(TARGET_SELECT,1,221,MARKER_REFERENCE);
        frame(nextFrame,1,1);nextFrame++;
        if(targetReport.reason!=REPORT_INVALID_REQUEST || targetReport.targetSelected)
            $fatal(1,"reference must use digit F");
        // Identity remains frame-bound even if a malformed peer reuses a tag.
        request(TARGET_SELECT,1,222,MARKER_BAY);
        @(negedge clk);frameObservation.boundRequest=activeRequest;
        frameObservation.boundRequest.markerType=MARKER_FUNCTION;
        frameObservation.frameId=nextFrame;nextFrame++;
        frameObservation.matchCount=1;frameValid=1;
        tick();checkNoMeasurement();
        if(targetReport.reason!=REPORT_REQUEST_CHANGED || targetReport.markerType!=MARKER_FUNCTION)
            $fatal(1,"red1 was relabelled blue1");
        @(negedge clk);frameValid=0;
        restart(); activeCfgVersion=0;
        request(TARGET_SELECT,1,65535);
        frame(65534,1,1); frame(65535,1,1); frame(0,1,1);
        if(!targetReport.locked) $fatal(1,"frame wrap must be legal");
        frame(65534,1,1);
        checkNoMeasurement();
        // A stalled visible record survives target changes and newer frames.
        restart(); request(TARGET_SELECT,2,1);
        @(negedge clk); targetReportReady=0;
        frame(1,1,1); savedReport=targetReport;
        frame(2,1,1); frame(3,1,1); frame(4,1,1);
        if(targetReport!==savedReport || reportDropCount!=2) $fatal(1,"stall stability/drop count");
        request(TARGET_SELECT,4,2);
        if(targetReport!==savedReport) $fatal(1,"request changed presented payload");
        @(negedge clk); targetReportReady=1;
        tick();
        if(targetReport.frameId!=4 || !targetReport.locked || targetReport.requestTag!=1)
            $fatal(1,"newest pending report must retain historical identity");
        tick();
        if(targetReportValid) $fatal(1,"queue drains exactly once");
        $display("PASS targetTracker_tb");
        $finish;
    end
    initial begin #200000; $fatal(1,"timeout targetTracker_tb"); end
endmodule
