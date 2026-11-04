// CCTL v1: one held 64-bit transaction, immutable 16-word status snapshot.
// CLOCK_50 domain; source word must be stable for three cycles. No wheel override.
module chassisDebug #(
 parameter logic [31:0] BUILD_ID=32'hE7070001,
 parameter int LEASE_US=500000
)(
 input logic clk,reset,
 input logic [31:0] timeUs,
 input logic [511:0] statusWords,
 output logic [1:0] mode,
 output logic modeChanged,debugStart,debugStop,
 output wire injectLeaseValid,
 output wire [31:0] leaseAgeUs,
 output logic scanCalibrated,
 output logic [31:0] scanBudgetUs,
 output logic [31:0] observation0,observation1,
 output logic templateValid
);
 logic [63:0] sourceWord,previousSource,stableSource;
 logic [1:0] stableCount,staged;
 logic haveBaseline,ackToggle,leaseSeen;
 logic [6:0] errorCode;
 logic [31:0] heartbeatUs,stage0,stage1;
 logic [511:0] frozenWords;
 logic [31:0] selectedWord;
 wire [31:0] metaWord={8'd1,8'd16,ackToggle,errorCode,8'd0};
 wire [127:0] probeWord={32'h4343544c,BUILD_ID,metaWord,selectedWord};
 snapshot_probes #(.ID("CCTL"),.SW(64),.PW(128)) probes(
   .clk(clk),.source(sourceWord),.probe(probeWord));
 assign leaseAgeUs=leaseSeen ? timeUs-heartbeatUs : 32'hffffffff;
 assign injectLeaseValid=mode==2 && leaseSeen && !leaseAgeUs[31] && leaseAgeUs<LEASE_US;
 always_comb begin
   selectedWord=0;
   if(stableSource[55:48]<16) selectedWord=frozenWords[stableSource[51:48]*32+:32];
 end
 always_ff @(posedge clk) begin
   if(reset) begin
     previousSource<=0;stableSource<=0;stableCount<=0;haveBaseline<=0;
     ackToggle<=0;errorCode<=0;mode<=0;modeChanged<=0;debugStart<=0;debugStop<=0;
     leaseSeen<=0;heartbeatUs<=0;scanCalibrated<=0;scanBudgetUs<=10000000;
     stage0<=0;stage1<=0;staged<=0;observation0<=0;observation1<=0;templateValid<=0;frozenWords<=0;
   end else begin
     modeChanged<=0;debugStart<=0;debugStop<=0;
     if(sourceWord!=previousSource)begin previousSource<=sourceWord;stableCount<=1;end
     else begin
       if(stableCount<3)stableCount<=stableCount+2'd1;
       if(stableCount>=2)begin
         stableSource<=sourceWord;
         // Consume the pre-reset source as a baseline; old ARM is never replayed.
         if(!haveBaseline)begin haveBaseline<=1;ackToggle<=sourceWord[63];end
         else if(sourceWord[63]!=ackToggle)begin
           ackToggle<=sourceWord[63];errorCode<=0;
           if(sourceWord[62:60]!=0 || sourceWord[47:32]!=0)errorCode<=1;
           else case(sourceWord[59:56])
             1: if(sourceWord[31:0]<=2)begin
                 // Even reselecting the current mode is an explicit task boundary.
                 mode<=sourceWord[1:0];modeChanged<=1;debugStop<=1;
                 leaseSeen<=0;templateValid<=0;staged<=0;
               end else errorCode<=2;
             2: begin
                 frozenWords<=statusWords;
                 frozenWords[14*32+:32]<=leaseAgeUs;
                 frozenWords[15*32+:32]<={injectLeaseValid,templateValid,scanCalibrated,observation0[20],26'd0,mode};
               end
             3: if(mode==1 || (mode==2 && (!injectLeaseValid || !templateValid)))errorCode<=3;
                else debugStart<=1;
             4: debugStop<=1;
             5: begin stage0<=sourceWord[31:0];staged[0]<=1;end
             6: begin stage1<=sourceWord[31:0];staged[1]<=1;end
             7: if(mode!=2 || staged!=3)errorCode<=4;
                else if(stage0[7:0]>=240 || stage0[16:8]>=320 ||
                        stage0[23:21]!=0 || stage1[31:17]!=0 ||
                        stage1[7:0]>240 || stage1[16:8]>320)errorCode<=2;
                else begin observation0<=stage0;observation1<=stage1;templateValid<=1;staged<=0;end
             8: if(mode!=2)errorCode<=3;else begin heartbeatUs<=timeUs;leaseSeen<=1;end
             9: if(sourceWord[31:0]<1000000 || sourceWord[31:0]>120000000)errorCode<=2;
                else begin scanBudgetUs<=sourceWord[31:0];scanCalibrated<=0;debugStop<=1;end
             10: if(sourceWord[31:0]>1)errorCode<=2;
                 else begin scanCalibrated<=sourceWord[0];debugStop<=1;end
             default:errorCode<=1;
           endcase
         end
       end
     end
   end
 end
endmodule
