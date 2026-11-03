`timescale 1ns/1ps
// Independent / and % expectations over every representable unsigned input.
// Only the production implementation uses reciprocal multiplication.
module memberBVgaArithmetic_tb;
    logic clk=0;
    always #5 clk=~clk;
    memberBVgaDiagnostics dut(.clk(clk),.reset(1'b1),.showCandidates(1'b0),.showCentre(1'b0),
        .debugWords((perception_pkg::DEBUG_WORD_COUNT*32)'(0)),.rawDebugWords((perception_pkg::DEBUG_WORD_COUNT*32)'(0)),.rawData(30'd0),.rawSop(1'b0),.rawEop(1'b0),.rawAccept(1'b0),
        .inData(30'd0),.inSop(1'b0),.inEop(1'b0),.inValid(1'b0),.inReady(),
        .outData(),.outSop(),.outEop(),.outValid(),.outReady(1'b1));
    initial begin
        for(int value=0;value<1024;value++)begin
            if(dut.divideSix(10'(value))!==8'(value/6)||dut.remainderSix(10'(value))!==3'(value%6))
                $fatal(1,"FAIL reciprocal /6 or %%6 value%0d",value);
            if(value<512)begin
                if(dut.divideTen(9'(value))!==6'(value/10)||dut.remainderTen(9'(value))!==4'(value%10)||
                   dut.divideHundred(9'(value))!==3'(value/100))
                    $fatal(1,"FAIL reciprocal decimal conversion value%0d",value);
            end
        end
        $display("PASS memberBVgaArithmetic_tb: 3584 exhaustive division/remainder comparisons");
        $finish;
    end
endmodule
