`timescale 1ns/1ps
module tb_chassis_init;
 // Tool compatibility: version 5.050 crashes on hierarchical enum literals (dut.SEND/LOAD_FB).
 // Match the sender's unchanged enum encoding without changing the checks.
 localparam logic [1:0] SENDER_SEND=2'd1,SENDER_LOAD_FB=2'd2;
 logic clk=0,reset=1,armed=0,softReset=0,initAllowed=0,feedback=0;
 logic signed[6:0] l=0,r=0;
 wire tx,busy,zeroSent,initSent;
 always #10 clk=~clk;
 localparam string ZERO="{\"T\":1,\"L\":0.00,\"R\":0.00}\n";
 localparam string FLOW="{\"T\":131,\"cmd\":0}\n";
 localparam string MOVE="{\"T\":1,\"L\":0.05,\"R\":0.05}\n";
 localparam string CHANGE="{\"T\":1,\"L\":0.05,\"R\":0.04}\n";
 localparam string FB="{\"T\":130}\n";
 chassis_command #(.CLKS_PER_BIT(4),.PERIOD_CLKS(10000),.USE_WHEEL_REQUESTS(1),.INIT_FLOWOFF(1)) dut(
   .clk(clk),.reset(reset),.armed(armed),.motion(2'd0),.speed(2'd0),.left_cm_s(l),.right_cm_s(r),
   .feedback(feedback),.initAllowed(initAllowed),.softReset(softReset),.initSent(initSent),
   .tx(tx),.busy(busy),.zeroSent(zeroSent));
 // Feature-off instantiation deliberately leaves the new inputs unconnected,
 // preserving legacy named-port clients and making local readiness unconditional.
 wire legacyReady;
 chassis_command #(.CLKS_PER_BIT(4),.PERIOD_CLKS(10000),.USE_WHEEL_REQUESTS(1)) legacy(
   .initAllowed(1'b0),.softReset(1'b0),
   .clk(clk),.reset(reset),.armed(1'b0),.motion(2'd0),.speed(2'd0),.left_cm_s(7'sd0),.right_cm_s(7'sd0),
   .feedback(1'b0),.initSent(legacyReady),.tx(),.busy(),.zeroSent());
 int checks=0,lineCount=0,configStarts=0,initRises=0;
 string lines[0:511];
 logic previousInit=0;
 task automatic ck(input bit ok,input string label);
   checks++;if(!ok)$fatal(1,"%s lines=%0d state=%0d rem=%0d ready=%0b zero=%0b",label,lineCount,dut.state,dut.remaining,initSent,zeroSent);
 endtask
 task automatic tick(input int n=1);repeat(n)begin @(posedge clk);#1;end endtask
 task automatic idle;wait(!busy);@(negedge clk);endtask
 task automatic nextLine(input int afterIndex,input string expected,input string label);
   wait(lineCount>afterIndex);ck(lines[afterIndex]==expected,label);
 endtask
 task automatic waitConfigStart;
   wait(dut.state==SENDER_SEND && dut.messageIsInit);@(negedge clk);
 endtask
 task automatic reinitialize(input bit allow=1);
   idle();dut.timer=0; // isolate the scenario from unrelated heartbeat phase
   armed=0;l=0;r=0;initAllowed=allow;softReset=1;tick(3);
   ck(!initSent,"soft reset clears ready without resetting UART");
   @(negedge clk);softReset=0;tick();
 endtask
 task automatic readLine;
   logic[7:0] ch;string line;line="";
   for(int n=0;n<29;n++)begin
     @(negedge tx);#40;
     for(int b=0;b<8;b++)begin #80;ch[b]=tx;end
     #80;ck(tx===1,"complete UART stop bit");line={line,ch};
     if(ch==10)begin
       ck(lineCount<512,"bounded capture");
       ck(line==ZERO || line==FLOW || line==MOVE || line==CHANGE || line==FB,"whole exact JSON only");
       if(line==FLOW)ck(!initSent,"initSent does not rise at LF start/middle stop bit");
       lines[lineCount]=line;lineCount++;return;
     end
   end
   $fatal(1,"missing LF");
 endtask
 initial forever readLine();
 always @(posedge clk) begin
   if(!reset && dut.tx_valid && dut.tx_ready && dut.messageIsInit) configStarts++;
   #1;
   if(initSent && !previousInit)begin
     initRises++;ck(dut.tx_ready && tx && !busy,"ready rises only after complete final UART stop bit");
   end
   previousInit=initSent;
 end
  localparam int MAXLEN=28;
  localparam logic [8*11-1:0] P1="{\"T\":1,\"L\":";
  localparam logic [8*5-1:0] P2=",\"R\":";
  localparam logic [8*2-1:0] P3="}\n";
    function automatic logic [MAXLEN*8+7:0] reference_wheel_msg(input logic enable,
      input logic signed [6:0] l, r);
      logic [6:0] lm,rm;
      logic [15:0] ld,rd;
      logic ln,rn;
      logic [MAXLEN*8-1:0] t;
      begin
        lm=l<0 ? 7'(-l):7'(l);rm=r<0 ? 7'(-r):7'(r);
        if(!enable || lm>15 || rm>15) begin lm=0;rm=0;end
        ln=l<0 && lm!=0;rn=r<0 && rm!=0;
        ld={8'(48+(lm>=10)),8'(48+(lm>=10 ? lm-10:lm))};
        rd={8'(48+(rm>=10)),8'(48+(rm>=10 ? rm-10:rm))};
        t='0;
        case({ln,rn})
          2'b00:begin t[MAXLEN*8-1 -: 26*8]={P1,"0.",ld,P2,"0.",rd,P3};return {8'd26,t};end
          2'b11:begin t[MAXLEN*8-1 -: 28*8]={P1,"-0.",ld,P2,"-0.",rd,P3};return {8'd28,t};end
          2'b10:begin t[MAXLEN*8-1 -: 27*8]={P1,"-0.",ld,P2,"0.",rd,P3};return {8'd27,t};end
          default:begin t[MAXLEN*8-1 -: 27*8]={P1,"0.",ld,P2,"-0.",rd,P3};return {8'd27,t};end
        endcase
      end
    endfunction
  int asciiChecks=0;
  task automatic ascii_equivalence;
    logic [MAXLEN*8+7:0] actual,expected;
    asciiChecks=0;
    for(int enable=0;enable<2;enable++)begin
      for(int l=-64;l<64;l++)begin
        for(int r=-64;r<64;r++)begin
          actual=dut.wheel_msg(1'(enable),7'(l),7'(r));
          expected=reference_wheel_msg(1'(enable),7'(l),7'(r));
          if(actual!==expected)$fatal(1,"ASCII mismatch enable=%0d L=%0d R=%0d",enable,l,r);
          asciiChecks++;
        end
      end
    end
  endtask
 initial begin
   int first,started,oldReady;
   ascii_equivalence();
   tick(3);@(negedge clk);reset=0;tick();
   ck(legacyReady && !initSent,"generic off bypasses readiness; enabled boot starts pending");
   nextLine(0,ZERO,"first boot line is STOP");wait(zeroSent);tick(3);
   ck(!initSent && lineCount==1,"initAllowed false cannot issue config");
   @(negedge clk);initAllowed=1;waitConfigStart();
   ck(zeroSent && dut.sentL==0 && dut.sentR==0,"config starts only after real zero, retaining wheel baseline");
   // Arrange a real timer tick during config. It must be remembered, not lost.
   dut.timer=14'd9990;tick(15);ck(dut.heartbeatPending,"wheel heartbeat due during config is retained");
   nextLine(1,FLOW,"boot emits exact T131 cmd0");wait(initSent);
   nextLine(2,ZERO,"retained heartbeat becomes next complete zero");idle();
   oldReady=initRises;tick(12000);ck(initRises==oldReady,"one initialization per request");
   for(int i=3;i<lineCount;i++)ck(lines[i]==ZERO,"ordinary wheel heartbeat continues without repeated init");

   // Reinitialization denied by true task/mode qualification remains pending,
   // but STOP/ordinary zero and read-only operation continue.
   reinitialize(0);wait(zeroSent);tick(2000);ck(!initSent,"disallowed task/mode cannot initialize");
   first=lineCount;initAllowed=1;waitConfigStart();nextLine(first,FLOW,"permission later permits exactly one config");wait(initSent);idle();

   // Every byte, including LF: an asynchronous stop request must complete the
   // current config and send a whole zero next, never concatenate/truncate.
   for(int byteIndex=0;byteIndex<18;byteIndex++)begin
     reinitialize();waitConfigStart();first=lineCount;started=configStarts;
     wait(configStarts>=started+byteIndex+1);@(negedge clk);armed=1;tick(2);
     @(negedge clk);armed=0;tick();ck(dut.stop_pending,"STOP remembered inside config");
     nextLine(first,FLOW,"STOP preserves whole current config");
     nextLine(first+1,ZERO,"STOP is the next whole packet at every config byte");wait(initSent);idle();
   end

   // A requested wheel change during config cannot overwrite the packet or be
   // swallowed by config completion. A following change still sends promptly.
   reinitialize();waitConfigStart();first=lineCount;
   @(negedge clk);armed=1;l=5;r=5;tick();
   nextLine(first,FLOW,"in-flight config is atomic under new wheel request");
   nextLine(first+1,MOVE,"new request survives init completion");idle();ck(!zeroSent,"nonzero motion invalidates old zeroSent");
   first=lineCount;r=4;nextLine(first,CHANGE,"subsequent wheel update is not swallowed");idle();
   first=lineCount;armed=0;nextLine(first,ZERO,"normal STOP priority remains");wait(zeroSent);idle();

   // Soft reset while a nonzero packet is in flight must preserve that packet,
   // then zero -> fresh config. It does not reset uart_tx or the packet shifter.
   first=lineCount;armed=1;l=5;r=5;wait(busy && dut.messageIsMotion && !dut.messageIsZero);tick(100);
   @(negedge clk);softReset=1;armed=0;tick(3);ck(!initSent && !zeroSent,"soft reset invalidates readiness and old zero proof");
   @(negedge clk);softReset=0;
   nextLine(first,MOVE,"soft reset preserves in-flight nonzero JSON");
   nextLine(first+1,ZERO,"soft reset schedules zero next");
   nextLine(first+2,FLOW,"soft reset reinitializes only after zero");wait(initSent);idle();

   // At every config byte a soft reset invalidates old completion. The old
   // complete line is followed by a new zero and a newly completed config.
   for(int byteIndex=0;byteIndex<18;byteIndex++)begin
     reinitialize();waitConfigStart();first=lineCount;started=configStarts;oldReady=initRises;
     wait(configStarts>=started+byteIndex+1);@(negedge clk);softReset=1;tick(3);
     @(negedge clk);softReset=0;
     nextLine(first,FLOW,"soft reset never truncates config at any byte");tick(3);
     ck(initRises==oldReady && !initSent,"old in-flight initialization cannot satisfy new reset request");
     nextLine(first+1,ZERO,"reset config completion is followed by zero");
     nextLine(first+2,FLOW,"fresh config follows reset zero");wait(initSent);idle();
   end

   // Generic caller may assert softReset without dropping armed on that edge.
   // The packet-load stop condition must nevertheless dominate wheel motion.
   first=lineCount;armed=1;l=5;r=5;softReset=1;tick();
   @(negedge clk);armed=0;softReset=0;
   nextLine(first,ZERO,"same-edge soft reset cannot load a new nonzero packet");
   wait(initSent);idle();

   // Existing telemetry polling remains subordinate to an arriving STOP.
   feedback=1;first=lineCount;armed=1;l=5;r=5;
   wait(dut.state==SENDER_LOAD_FB);@(negedge clk);armed=0;tick();
   nextLine(first,MOVE,"motion before deferred feedback remains complete");
   nextLine(first+1,ZERO,"STOP arriving at LOAD_FB outranks optional query");feedback=0;
   wait(zeroSent);idle();
   $display("PASS tb_chassis_init checks=%0d UART=%0d initCompletions=%0d configBytes=%0d asciiEquivalence=%0d",checks,lineCount,initRises,configStarts,asciiChecks);$finish;
 end
 initial begin #50000000;$fatal(1,"watchdog lines=%0d state=%0d rem=%0d",lineCount,dut.state,dut.remaining);end
endmodule
