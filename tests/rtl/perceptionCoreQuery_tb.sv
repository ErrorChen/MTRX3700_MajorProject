`timescale 1ns/1ps
// PROTOCOL_READER_INJECTION: only the reader's result and owned input bank are
// controlled. The real aggregate scan, BJ pairing, query RAM/router and target
// tracker execute unchanged. This is not pixel-recognition or camera evidence.
module perceptionCoreQuery_tb;
    import perception_pkg::*;
    import candidate_pkg::*;
    import vision_pkg::*;
    logic clk=0,pclk=0,reset=1,resetPclk=1;
    always #10 clk=~clk;
    always #25 pclk=~pclk;
    logic cameraFrameStart=0,cameraPixelValid=0;
    logic [15:0] cameraPixel=0;
    logic [9:0] cameraX=0;
    logic [8:0] cameraY=0;
    logic [31:0] timeUs=0;
    logic interactionEnable=0,interactionPermit=0,debugCalArm=0,debugSpeechArm=0;
    logic debugInteractionArmReady;
    logic [1:0] orientationProfile=0;
    logic bypassPerspective=0,processingEnable=1;
    targetRequest_t targetRequest='0;
    logic targetRequestValid=0,targetRequestReady;
    targetReport_t targetReport;
    logic targetReportValid,targetReportReady=1;
    queryResult_t queryResult,heldQuery;
    logic queryResultValid,queryResultReady=0,queryBusy;
    userEvent_t userEvent;
    logic userEventValid,userEventReady=1;
    perceptionStatus_t status;
    logic [DEBUG_WORD_COUNT*32-1:0] debugWords;
    logic completedFrame;
    logic [15:0] completedFrameId;
    markerArray_t markerDrive;
    logic readerDoneDrive=0,candidateDrive=0;
    logic [31:0] latestCaptureUs;
    integer checks=0,queryItems=0;
    perceptionCore dut(.*);
    always @(posedge clk) if(!reset) timeUs<=timeUs+1;

    task automatic tick;
        @(posedge clk);#1;
    endtask

    function automatic marker_t marker(input bit accepted,blue,input integer digit,
        x0,x1,y0,y1,quality);
        marker_t value;
        value='0;value.accepted=accepted;value.isBlue=blue;value.digit=4'(digit);
        value.xMin=9'(x0);value.xMax=9'(x1);value.yMin=8'(y0);value.yMax=8'(y1);
        value.quality=8'(quality);
        return value;
    endfunction

    task automatic request(input targetOperation_t op,input markerType_t kind,input integer digit,tag);
        bit accepted;
        @(negedge clk);targetRequest.operation=op;targetRequest.markerType=kind;
        targetRequest.digit=4'(digit);targetRequest.requestTag=16'(tag);targetRequestValid=1;
        #1;accepted=0;
        for(int cycles=0;cycles<200;cycles++) begin
            // Sample readiness before the transfer; accepting a query changes
            // its ready output on the same rising edge.
            if(targetRequestReady) begin tick();accepted=1;break;end
            tick();@(negedge clk);
        end
        if(!accepted)$fatal(1,"core request timeout op=%0d",op);
        @(negedge clk);targetRequestValid=0;
    endtask

    task automatic completeFrame(input integer id,input bit good);
        bit seen;
        @(negedge clk);
        dut.bankMeta[0]='0;dut.bankMeta[0].boundRequest=dut.activeRequest;
        dut.bankMeta[0].frameId=16'(id);dut.bankMeta[0].captureStartUs=timeUs;
        dut.bankMeta[0].configVersion=status.activeCfgVersion;dut.bankMeta[0].frameGood=good;
        latestCaptureUs=timeUs;
        dut.bankCandidates[0]='0;dut.bankColours[0]=0;dut.bankOrientation[0]=0;
        for(int slot=0;slot<6;slot++) begin
            dut.bankCandidates[0][slot].valid=1;
            dut.bankCandidates[0][slot].xmin=markerDrive[slot].xMin;
            dut.bankCandidates[0][slot].xmax=markerDrive[slot].xMax;
            dut.bankCandidates[0][slot].ymin=markerDrive[slot].yMin;
            dut.bankCandidates[0][slot].ymax=markerDrive[slot].yMax;
            dut.bankColours[0][slot]=markerDrive[slot].isBlue;
        end
        dut.bankRedCount[0]=2;dut.bankBlueCount[0]=4;
        dut.bankState[0]=dut.READING;dut.bankState[1]=dut.FREE;dut.haveWriteBank=0;
        readerDoneDrive=1;tick();
        @(negedge clk);readerDoneDrive=0;seen=0;
        for(int cycles=0;cycles<100;cycles++) begin
            tick();if(completedFrame)begin seen=1;break;end
        end
        if(!seen||completedFrameId!=id||dut.pairCount!=1)
            $fatal(1,"real aggregate/BJ pairing failed frame=%0d pairs=%0d",id,dut.pairCount);
        tick();
        if(!targetReportValid||targetReport.frameId!=id)
            $fatal(1,"completed frame did not reach real tracker");
        checks++;
    endtask

    task automatic waitQuery;
        bit seen;
        seen=0;
        for(int cycles=0;cycles<150;cycles++)begin
            if(queryResultValid)begin seen=1;break;end
            tick();
        end
        if(!seen)$fatal(1,"core query response timeout");
    endtask

    task automatic checkItemGeometry;
        if(queryResult.markerType==MARKER_FUNCTION&&queryResult.digit==1)begin
            if(queryResult.centreU!=55||queryResult.centreV!=269||queryResult.boxWidth!=71||
               queryResult.boxHeight!=61||queryResult.quality!=211)$fatal(1,"red1 query geometry");
        end else if(queryResult.markerType==MARKER_FUNCTION&&queryResult.digit==2)begin
            if(queryResult.centreU!=175||queryResult.centreV!=269||queryResult.boxWidth!=71||
               queryResult.boxHeight!=61)$fatal(1,"red2 query geometry");
        end else if(queryResult.markerType==MARKER_BAY&&queryResult.digit==1)begin
            if(!((queryResult.centreU==45&&queryResult.centreV==179)||
                 (queryResult.centreU==50&&queryResult.centreV==99))||
               queryResult.boxWidth!=51||queryResult.boxHeight!=41)$fatal(1,"blue1 query geometry");
        end else if(queryResult.markerType==MARKER_REFERENCE&&queryResult.digit==15)begin
            if(queryResult.centreU!=101||queryResult.centreV!=269||queryResult.boxWidth!=14||
               queryResult.boxHeight!=61||queryResult.quality!=211)$fatal(1,"BJ ownership/quality/geometry");
        end else $fatal(1,"unknown blue region appeared as recognised item");
    endtask

    task automatic drainQuery(input integer tag,id,count,input queryReason_t reason);
        integer red1,red2,blue1,reference;
        logic [31:0] stamp;
        bit firstBlue,secondBlue;
        red1=0;red2=0;blue1=0;reference=0;firstBlue=0;secondBlue=0;stamp=0;
        for(int item=0;item<(count==0?1:count);item++)begin
            waitQuery();
            if(item==0)stamp=queryResult.captureStartUs;
            if(queryResult.requestTag!=tag||queryResult.frameId!=id||queryResult.count!=count||
               queryResult.index!=item||queryResult.last!==(item==(count==0?0:count-1))||
               queryResult.reason!=reason||queryResult.configVersion!=0||queryResult.captureStartUs!=stamp)
                $fatal(1,"query packet identity/count/last frame=%0d index=%0d",queryResult.frameId,item);
            if(count==0)begin
                if(queryResult.markerType!=MARKER_NONE||queryResult.digit!=15||queryResult.centreU||
                   queryResult.centreV||queryResult.boxWidth||queryResult.boxHeight||queryResult.quality)
                    $fatal(1,"invalid query retained old good data");
            end else begin
                checkItemGeometry();
                if(queryResult.markerType==MARKER_FUNCTION)begin
                    if(queryResult.digit==1)red1++;else red2++;
                end else if(queryResult.markerType==MARKER_REFERENCE)reference++;
                else begin
                    blue1++;
                    if(queryResult.centreV==179)firstBlue=1;else secondBlue=1;
                end
            end
            queryItems++;
            @(negedge clk);queryResultReady=1;tick();
            @(negedge clk);queryResultReady=0;
        end
        if(count==5&&(red1!=1||red2!=1||blue1!=2||reference!=1))$fatal(1,"LIST typed multiset");
        if(count==2&&(blue1!=2||!firstBlue||!secondBlue))$fatal(1,"GET did not return both real positions");
        if(queryBusy||queryResultValid)$fatal(1,"query did not drain exactly once");
        checks++;
    endtask

    initial begin
        markerDrive='0;
        markerDrive[0]=marker(1,0,1,20,80,20,90,211);
        markerDrive[1]=marker(1,1,1,120,160,20,70,220);
        markerDrive[2]=marker(1,1,1,200,240,25,75,219);
        markerDrive[3]=marker(1,0,2,20,80,140,210,218);
        markerDrive[4]=marker(0,1,15,20,80,95,108,0); // unique red1-owned BJ
        markerDrive[5]=marker(0,1,15,250,280,160,180,0); // unknown blue block
        repeat(5)@(negedge clk);reset=0;resetPclk=0;
        force dut.readerBusy=1'b1;force dut.readerDone=readerDoneDrive;
        force dut.markers=markerDrive;force dut.readBank=1'b0;
        force dut.candidateValid=candidateDrive;
        tick();
        request(TARGET_SELECT,MARKER_BAY,1,10);completeFrame(1,1);
        if(!targetReport.ambiguous||targetReport.observed||targetReport.locked||
           targetReport.reason!=REPORT_DUPLICATE_ID)$fatal(1,"duplicate blue1 was arbitrarily selected");
        request(TARGET_LIST,MARKER_NONE,15,11);drainQuery(11,1,5,QUERY_OK);
        request(TARGET_GET,MARKER_BAY,1,12);drainQuery(12,1,2,QUERY_MULTIPLE);
        request(TARGET_GET,MARKER_FUNCTION,1,13);drainQuery(13,1,1,QUERY_OK);
        request(TARGET_GET,MARKER_REFERENCE,15,14);drainQuery(14,1,1,QUERY_OK);
        if(dut.activeRequest.requestTag!=10||dut.activeRequest.markerType!=MARKER_BAY)
            $fatal(1,"queries changed active tracking request");
        request(TARGET_SELECT,MARKER_FUNCTION,1,20);
        for(int id=2;id<=4;id++)begin
            completeFrame(id,1);
            if(!targetReport.observed||targetReport.markerType!=MARKER_FUNCTION||
               targetReport.digit!=1||targetReport.locked!==(id==4))$fatal(1,"red1 three-frame tracking");
        end
        request(TARGET_GET,MARKER_BAY,1,21);waitQuery();heldQuery=queryResult;
        completeFrame(5,1);
        if(queryResult!==heldQuery||!targetReport.locked||targetReport.requestTag!=20)
            $fatal(1,"stalled GET changed live red tracking or snapshot");
        request(TARGET_SELECT,MARKER_REFERENCE,15,30);
        for(int id=6;id<=8;id++)begin
            completeFrame(id,1);
            if(!targetReport.observed||targetReport.markerType!=MARKER_REFERENCE||
               targetReport.digit!=15||targetReport.locked!==(id==8)||
               targetReport.centreU!=101||targetReport.centreV!=269||targetReport.quality!=211||
               queryResult!==heldQuery)$fatal(1,"BJ tracking/held-query isolation");
        end
        drainQuery(21,4,2,QUERY_MULTIPLE);
        completeFrame(9,0);
        if(targetReport.observed||targetReport.locked)$fatal(1,"bad frame remained locked");
        request(TARGET_GET,MARKER_FUNCTION,1,40);drainQuery(40,9,0,QUERY_FRAME_BAD);
        completeFrame(10,1);
        if(targetReport.locked)$fatal(1,"bad frame did not clear confirmation");
        // Real core drop arbitration publishes a newer invalid frame into the
        // query store; no aggregate/observation/result signals are forced.
        @(negedge clk);dut.captureMeta='0;dut.captureMeta.boundRequest=dut.activeRequest;
        dut.captureMeta.frameId=11;dut.captureMeta.captureStartUs=timeUs;
        dut.captureMeta.configVersion=0;dut.haveWriteBank=0;candidateDrive=1;
        tick();@(negedge clk);candidateDrive=0;tick();
        if(targetReport.frameId!=11||targetReport.reason!=REPORT_RESOURCE_DROP||targetReport.observed)
            $fatal(1,"core drop did not invalidate target");
        request(TARGET_GET,MARKER_FUNCTION,1,41);drainQuery(41,11,0,QUERY_FRAME_BAD);
        $display("PASS perceptionCoreQuery_tb checks=%0d queryItems=%0d",checks,queryItems);
        $finish;
    end
    initial begin #2000000;$fatal(1,"timeout perceptionCoreQuery_tb");end
endmodule
