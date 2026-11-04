// IR is latched separately from recoverable sonar HOLD. POWER releases IR only;
// caller must provide a new full-press event for a later START.
module safety_arbiter #(parameter int ULTRASONIC_ESTOP_MM=250,SONAR_RESUME_MM=300)(
 input logic clk,reset,power_frame,estop_frame,motion_enable,
 input logic taskArmed,cancel,modePermit,distanceSample,
 input logic distance_valid,input logic [11:0] distance_mm,
 output wire permit,taskEnabled,output wire used,
 output logic estop,sonar_stop,
 output logic [2:0] reason
);
 logic [1:0] safeSamples;
 wire hazard=!distance_valid || distance_mm<=ULTRASONIC_ESTOP_MM;
 assign taskEnabled=taskArmed;
 assign used=taskArmed;
 assign permit=motion_enable && taskArmed && modePermit && !reset && !cancel && !estop_frame &&
   !estop && !sonar_stop && !hazard;
 always_comb begin
   if(estop || estop_frame)reason=1;
   else if(sonar_stop || hazard)reason=2;
   else if(!modePermit)reason=3;
   else reason=0;
 end
 always_ff @(posedge clk)begin
   if(reset)begin estop<=0;sonar_stop<=1;safeSamples<=0;end
   else begin
     if(estop_frame)estop<=1;
     else if(power_frame && estop)estop<=0;
     if(hazard)begin sonar_stop<=1;safeSamples<=0;end
     else if(distanceSample)begin
       if(distance_mm>=SONAR_RESUME_MM)begin
         if(safeSamples==2)begin sonar_stop<=0;safeSamples<=3;end
         else if(safeSamples!=3)safeSamples<=safeSamples+2'd1;
       end else safeSamples<=0;
     end
   end
 end
endmodule
