`timescale 1ns/1ps
module tb_scheme_c_link;
 `include "board_fixture.svh"
 assign gpio[29]=1'b0;
 logic [31:0] simTime=10000,necCode=0;
 logic necValid=0,rangeValid=1;
 logic [11:0] rangeMm=1000;
 task automatic frame_at;
 simTime+=1000;tick(2);observe(120);endtask
 task automatic three;
 frame_at();check(!dut.chassis.running,"post-fault frame 1 stopped");
 frame_at();check(!dut.chassis.running,"post-fault frame 2 stopped");
 frame_at();check(dut.chassis.running,"post-fault frame 3 resumes through real tracker");endtask
 task automatic abandon;
 tick();simTime+=100;dut.core.bankState[0]=dut.core.WRITING;
 force dut.core.writeBank=1'b0;force dut.core.haveWriteBank=1'b1;
 force dut.core.sof=1'b1;#1;
 check(dut.cameraAbandonEvent&&!dut.chassis.motionTargetValid&&!dut.chassis.running,
 "real Core abandon predicate immediately reaches C");
 tick();force dut.core.sof=1'b0;force dut.core.haveWriteBank=1'b0;
 tick(3);check(dut.status.faultFlags[0]&&!dut.cameraFifoFault,"abandon history separate from FIFO fault");
 // The fixture bypasses observation publication; supply its real bad-frame meaning.
 simTime+=100;observe(120,1,5);
 endtask
 initial begin
 force dut.timeUs=simTime;force dut.chassis.nec_valid=necValid;force dut.chassis.nec_code=necCode;
 force dut.chassis.sonar_u.distance_valid=rangeValid;force dut.chassis.sonar_u.distance_mm=rangeMm;
 force dut.core.candidateValid=1'b0;force dut.core.aggregateDone=1'b0;force dut.core.sof=1'b0;
 install_observation_fixture();sw[4:2]=5;tick(10);key[0]=1;tick(20);
 necCode=32'hed12ff00;necValid=1;tick();necValid=0;tick(12);
 three();abandon();three();abandon();three();
 check(dut.core.bufferDropCount==2,"both abandon events counted without clearing history");
 // Inject an actual source FIFO-full event in PCLK, through existing sticky CDC.
 @(negedge pclk);force dut.core.cameraBridge.fifoFull=1'b1;
 force dut.core.cameraBridge.pixelValid=1'b1;force dut.core.cameraBridge.pixelX=10'd0;
 force dut.core.cameraBridge.pixelY=9'd0;
 @(negedge pclk);release dut.core.cameraBridge.fifoFull;release dut.core.cameraBridge.pixelValid;
 release dut.core.cameraBridge.pixelX;release dut.core.cameraBridge.pixelY;tick(12);
 check(dut.core.cameraBridge.sourceFault&&dut.cameraFifoFault&&!dut.chassis.running,"real FIFO source loss crosses CDC and stops C");
 frame_at();frame_at();frame_at();check(!dut.chassis.motionTargetValid,"FIFO history forbids three-frame recovery");
 key[0]=0;tick(10);key[0]=1;tick(20);
 check(!dut.chassis.running&&!dut.chassis.control_u.taskActive&&!dut.cameraFifoFault,"shared KEY0 resets faults without automatic start");
 $display("PASS: tb_scheme_c_link checks=%0d",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
