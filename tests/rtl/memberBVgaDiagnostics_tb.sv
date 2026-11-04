`timescale 1ns/1ps
module memberBVgaDiagnostics_tb;
 import perception_pkg::*;
 logic clk=0,reset=1,showCandidates=1,showCentre=1;always #5 clk=~clk;
 logic [DEBUG_WORD_COUNT*32-1:0] debugWords=0,rawDebugWords=0,fixtureWords;
 logic [29:0] rawData=0,inData=0;wire [29:0] outData;
 logic inSop=0,inEop=0,inValid=0,outReady=0;
 wire inReady,outSop,outEop,outValid;
 wire rawSop=inSop,rawEop=inEop,rawAccept=inValid&&inReady;
 integer cycles=0,written=0,read=0,frameNumber=0,page0Checks=0,page1Checks=0;
 integer outputX=0,outputY=0,bankWrites=0,threeBankChecks=0,preemptedLoads=0;
 logic [9:0] bankWritten[0:2];logic [87:0] bankExpected[0:2][0:9];
 logic [1:0] expectedDisplayBank;logic [15:0] expectedDisplayScan;
 logic previousLoadPending=0,stalled=0;logic [31:0] heldPayload;
 perceptionStatus_t status;
 memberBVgaDiagnostics #(.PAGE_FRAMES(2)) dut(.*);
 always @(negedge clk)begin cycles++;outReady=!reset&&cycles%5!=0&&cycles%7!=0;end
 always @(posedge clk)if(!reset)begin
   if(stalled&&(!outValid||{outSop,outEop,outData}!==heldPayload))$fatal(1,"stalled diagnostic payload changed");
   stalled=outValid&&!outReady;heldPayload={outSop,outEop,outData};
   if(inValid&&inReady)begin
     written++;if(inSop)frameNumber++;
     if((frameNumber==2||frameNumber==4)&&dut.pixelY==70)begin
       if(dut.pixelX==10)begin
         if(!dut.textActive||dut.character!==(frameNumber==2?8'd48:8'd56))$fatal(1,"page slot tag not #0/#8");
         if(frameNumber==2)page0Checks++;else page1Checks++;
       end
       if(dut.pixelX==28)begin
         if(!dut.textActive||dut.character!==(frameNumber==2?8'd49:8'd51))$fatal(1,"tag substituted for recognised digit");
         if(frameNumber==2)page0Checks++;else page1Checks++;
       end
     end
     if((frameNumber==2||frameNumber==4)&&dut.pixelX==28&&dut.pixelY==116)begin
       if(!dut.textActive||dut.character!="U")$fatal(1,"rejected candidate not UNKNOWN");
       if(frameNumber==2)page0Checks++;else page1Checks++;
     end
     if((frameNumber==2||frameNumber==4)&&dut.pixelX==94&&dut.pixelY==116)begin
       if(!dut.textActive||dut.character!="5")$fatal(1,"rejection code did not survive page/publication");
       if(frameNumber==2)page0Checks++;else page1Checks++;
     end
     if((frameNumber==2||frameNumber==4)&&dut.pixelX==258&&dut.pixelY==0)begin
       if(!dut.textActive||dut.character!==(frameNumber==2?8'd49:8'd50))$fatal(1,"page label disagrees with held samples");
       if(frameNumber==2)page0Checks++;else page1Checks++;
     end
   end
   if(outValid&&outReady)begin
     read++;if(outSop)begin outputX=0;outputY=0;end
     if(outputX==350&&outputY==300&&outData!={10'd0,10'd900,10'd0})$fatal(1,"unmarked source pixel changed");
     if(outputX==639)begin outputX=0;outputY++;end else outputX++;
   end
 end
 always @(posedge clk)begin
   if(reset)begin
     for(int bank=0;bank<3;bank++)bankWritten[bank]=0;
     previousLoadPending=0;
   end else begin
     if(dut.acceptedRaw&&rawEop&&dut.conversionState==dut.IDLE)bankWritten[dut.freeBank]=0;
     if(dut.conversionState==dut.WAIT_CONVERSION&&dut.converterValid)begin
       if(dut.publishedReady&&dut.workBank==dut.publishedBank)$fatal(1,"writer overwrote published bank");
       if((dut.loadActive||dut.readPending)&&dut.workBank==dut.loadBank)$fatal(1,"writer overwrote pinned loader");
       bankWritten[dut.workBank][dut.conversionIndex]=1;
       bankExpected[dut.workBank][dut.conversionIndex]=dut.convertedRecord;bankWrites++;
       if(dut.conversionIndex==9&&bankWritten[dut.workBank]!==10'h3ff)$fatal(1,"partial page published");
     end
     if((dut.loadActive||dut.readPending)&&dut.publishedReady&&dut.loadBank!=dut.publishedBank&&
        dut.conversionState!=dut.IDLE&&dut.workBank!=dut.publishedBank&&dut.workBank!=dut.loadBank)threeBankChecks++;
     if(inValid&&inReady&&inSop)begin
       if(dut.loadActive||dut.readPending)preemptedLoads++;
       expectedDisplayBank=dut.publishedBank;expectedDisplayScan=dut.publishedScanId;
     end
     if(previousLoadPending&&!(dut.loadActive||dut.readPending)&&!(inValid&&inReady&&inSop))begin
       for(int slot=0;slot<10;slot++)if(dut.displayRecords[slot]!==bankExpected[expectedDisplayBank][slot])
         $fatal(1,"page mixed publication banks slot%0d",slot);
       if(dut.displayScanId!==expectedDisplayScan)$fatal(1,"page provenance changed during load");
     end
     previousLoadPending=dut.loadActive||dut.readPending;
   end
 end
 task automatic packet(input integer count,input bit mutate=0);
   for(int i=0;i<count;i++)begin
     @(negedge clk);#1;inValid=1;inSop=i==0;inEop=i==count-1;
     rawData={10'd0,10'd348,10'd736};inData={10'd0,10'd900,10'd0};
     if(mutate&&i==1000)begin debugWords=0;rawDebugWords=0;showCandidates=0;showCentre=0;end
     @(posedge clk);while(!inReady)@(posedge clk);
   end
   @(negedge clk);#1;inValid=0;inSop=0;inEop=0;
   repeat(600)@(negedge clk);
 endtask
 task automatic burst(input integer count);
   for(int i=0;i<count;i++)begin
     @(negedge clk);#1;inValid=1;inSop=i==0;inEop=i==count-1;rawData=0;inData=0;
     @(posedge clk);while(!inReady)@(posedge clk);
   end
 endtask
 task automatic checkPage(input bit page);
   if(dut.displayPage!==page||dut.displayUiVisible[7:0]!=8'hff)$fatal(1,"eight page slots not visible");
   for(int i=0;i<8;i++)begin
     if(!dut.displayRecords[i][79]||dut.displayRecords[i][54:31]!={8'd0,8'd87,8'd184}||
        dut.displayRecords[i][30:22]!=212||dut.displayRecords[i][21:14]!=255||dut.displayRecords[i][13:6]!=184)
       $fatal(1,"RGB/HSV page sample mismatch slot%0d",i);
     if(dut.displayUiTags[i]!={page,3'(i)}||dut.displayRecords[i][78]!==!i[0])$fatal(1,"candidate acceptance/tag changed");
   end
   // Centre association scans all16 descriptors, including the off-page one.
   if(!dut.displayRecords[8][79]||!dut.displayRecords[8][78]||dut.displayRecords[8][76:73]!=5)
     $fatal(1,"off-page accepted centre identity lost");
 endtask
 initial begin
   status='0;status.calibrated=1;status.activeCfgVersion=5;
   debugWords[0+:32]=32'h45425031;debugWords[1*32+:32]={16'(DEBUG_SCHEMA_VERSION),16'(PERCEPTION_CONTRACT_VERSION)};
   debugWords[3*32+:16]=99;debugWords[7*32+:16]=16'h3020;debugWords[9*32+:10]={5'd16,5'd0};
   debugWords[10*32+:76]=status;debugWords[(DEBUG_TAIL_BASE+1)*32+:4]=8;debugWords[(DEBUG_TAIL_BASE+3)*32]=1;
   for(int i=0;i<16;i++)begin
     debugWords[(24+4*i)*32+:32]=i[0]?32'h4f000500:(32'hc0000000|(32'(i%6+1)<<24));
     debugWords[(25+4*i)*32+:32]={7'd0,9'd50,7'd0,9'd90};
     debugWords[(26+4*i)*32+:32]={8'd0,8'd60,8'd0,8'd80};
   end
   debugWords[(25+4*10)*32+:32]={7'd0,9'd100,7'd0,9'd220};
   debugWords[(26+4*10)*32+:32]={8'd0,8'd90,8'd0,8'd150};
   debugWords[(DEBUG_TAIL_BASE+2)*32+3]=1;debugWords[(DEBUG_TAIL_BASE+2)*32+4+:4]=15;
   fixtureWords=debugWords;rawDebugWords=debugWords;
   repeat(3)@(negedge clk);reset=0;
   packet(640*480);packet(640*480);checkPage(0);
   if(dut.sampleCount[0]!=16||dut.sampleCount[8]!=64)$fatal(1,"4x4/8x8 exact sample counts");
   packet(640*480);packet(640*480);checkPage(1);
   if(page0Checks!=5||page1Checks!=5||!dut.displayRecords[7][0])$fatal(1,"page label/unknown/reason/reference coverage");
   packet(640*480,1);
   if(!dut.heldShowCandidates||!dut.heldShowCentre||dut.displayStatus.activeCfgVersion!=5)$fatal(1,"SOP snapshot changed mid-frame");
   packet(10);packet(1);
   if(dut.heldShowCentre||dut.heldShowCandidates||dut.displayRecords[8][79])$fatal(1,"partial-frame rejection/switch disable failed");
   debugWords=fixtureWords;rawDebugWords=fixtureWords;showCandidates=1;showCentre=1;
   rawDebugWords[(DEBUG_TAIL_BASE+3)*32]=0;packet(50);
   for(int i=0;i<8;i++)if(dut.sampleMeta[i][24])$fatal(1,"bad-frame metadata admitted ROI");
   rawDebugWords=fixtureWords;rawDebugWords[2*32+:32]=150001;packet(50);
   for(int i=0;i<8;i++)if(dut.sampleMeta[i][24])$fatal(1,"stale metadata admitted ROI");
   rawDebugWords=fixtureWords;
   for(int n=0;n<180;n++)begin debugWords[3*32+:16]=16'(200+n);rawDebugWords=debugWords;burst(1+(n*13)%31);end
   @(negedge clk);#1;inValid=0;inSop=0;inEop=0;repeat(600)@(negedge clk);
   burst(2);@(negedge clk);#1;inValid=0;inSop=0;inEop=0;
   while(!(dut.conversionState==dut.WAIT_CONVERSION&&dut.conversionIndex==9&&dut.converterValid))begin @(negedge clk);#1;end
   inValid=1;inSop=1;inEop=0;@(posedge clk);while(!inReady)@(posedge clk);
   @(negedge clk);#1;inSop=0;inEop=1;@(posedge clk);while(!inReady)@(posedge clk);
   @(negedge clk);#1;inValid=0;inEop=0;repeat(600)@(negedge clk);
   if(preemptedLoads==0||threeBankChecks==0||read!=written||outValid)$fatal(1,"bank ownership/backpressure/drain coverage");
   $display("PASS memberBVgaDiagnostics_tb two pages/all16 candidates, UNKNOWN/reason, exact RGB/HSV, centre, frozen page, partial-frame rejection, backpressure pixels=%0d bankWrites=%0d threeBank=%0d preemptions=%0d",read,bankWrites,threeBankChecks,preemptedLoads);
   $finish;
 end
 initial begin #100000000;$fatal(1,"diagnostic paging watchdog");end
endmodule
