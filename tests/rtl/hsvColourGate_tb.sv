`timescale 1ns/1ps
// Exhaustive RGB565 expansion plus exact RGB888 boundary tests. The oracle
// independently computes real-valued HSV, rather than repeating the RTL's
// division-free comparisons. This is RTL_SIM evidence for a mathematical gate,
// not CAMERA_HW evidence for unmeasured lighting or exposure conditions.
module hsvColourGate_tb;
    logic [23:0] rgb=24'd0;
    logic [7:0] redMinimum=8'd48,blueMinimum=8'd32;
    logic [1:0] colourMask;
    logic [15:0] packed565;
    logic [1:0] expectedMask;
    integer checks=0,redCount,blueCount,neitherCount;
    hsvColourGate dut(.*);

    function automatic logic [1:0] hsvOracle(
        input logic [23:0] sample,
        input logic [7:0] redFloor,blueFloor
    );
        real r,g,b,v,minimum,delta,saturation,hue;
        logic redMatch,blueMatch;
        begin
            r=real'(sample[23:16])/255.0;
            g=real'(sample[15:8])/255.0;
            b=real'(sample[7:0])/255.0;
            v=r;
            if(g>v) v=g;
            if(b>v) v=b;
            minimum=r;
            if(g<minimum) minimum=g;
            if(b<minimum) minimum=b;
            delta=v-minimum;
            saturation=0.0;
            hue=0.0;
            redMatch=0;
            blueMatch=0;
            if(delta>0.0&&v>0.0) begin
                saturation=delta/v;
                if(v==r) hue=60.0*((g-b)/delta);
                else if(v==g) hue=60.0*(2.0+(b-r)/delta);
                else hue=60.0*(4.0+(r-g)/delta);
                if(hue<0.0) hue=hue+360.0;
                // Epsilon only compensates binary-real rounding at exact
                // rational boundaries; nearest RGB888 hue steps are much larger.
                redMatch=(saturation>=0.5-1.0e-10)&&
                    (v>=real'(redFloor)/255.0-1.0e-10)&&
                    ((hue>=336.0-1.0e-10)||(hue<=1.0e-10));
                blueMatch=(saturation>=0.5-1.0e-10)&&
                    (v>=real'(blueFloor)/255.0-1.0e-10)&&
                    (hue>=200.0-1.0e-10)&&(hue<=250.0+1.0e-10);
            end
            hsvOracle=2'd0;
            if(redMatch&&!blueMatch) hsvOracle=2'd1;
            else if(blueMatch&&!redMatch) hsvOracle=2'd2;
        end
    endfunction

    task automatic checkSample(input logic [23:0] sample);
        begin
            rgb=sample;
            expectedMask=hsvOracle(sample,redMinimum,blueMinimum);
            #1;
            if(colourMask!==expectedMask)
                $fatal(1,"HSV mismatch RGB=%06h floors=%0d/%0d actual=%0d expected=%0d",
                    sample,redMinimum,blueMinimum,colourMask,expectedMask);
            checks++;
        end
    endtask

    task automatic checkBoundary(input logic [23:0] sample,input logic [1:0] expected);
        begin
            checkSample(sample);
            if(colourMask!==expected)
                $fatal(1,"Explicit HSV boundary mismatch RGB=%06h actual=%0d expected=%0d",
                    sample,colourMask,expected);
        end
    endtask

    initial begin
        for(integer profile=0;profile<2;profile++) begin
            redMinimum=(profile==0)?8'd48:8'd37;
            blueMinimum=(profile==0)?8'd32:8'd30;
            redCount=0;
            blueCount=0;
            neitherCount=0;
            for(integer pixel=0;pixel<65536;pixel++) begin
                packed565=16'(pixel);
                // Standard bit-replication expansion, not zero padding.
                checkSample({packed565[15:11],packed565[15:13],
                    packed565[10:5],packed565[10:9],packed565[4:0],packed565[4:2]});
                case(colourMask)
                    2'd1:redCount++;
                    2'd2:blueCount++;
                    default:neitherCount++;
                endcase
            end
            if(redCount==0||blueCount==0||neitherCount==0)
                $fatal(1,"Exhaustive sweep did not exercise all output classes");
            $display("HSV profile=%0d floors=%0d/%0d RGB565=65536 red=%0d blue=%0d neither=%0d",
                profile,redMinimum,blueMinimum,redCount,blueCount,neitherCount);
            for(integer grey=0;grey<256;grey++)
                checkBoundary({8'(grey),8'(grey),8'(grey)},2'd0);
            // V thresholds are inclusive, and the separate floors are honoured.
            checkBoundary({(redMinimum-8'd1),16'd0},2'd0);
            checkBoundary({redMinimum,16'd0},2'd1);
            checkBoundary({(redMinimum+8'd1),16'd0},2'd1);
            checkBoundary({16'd0,(blueMinimum-8'd1)},2'd0);
            checkBoundary({16'd0,blueMinimum},2'd2);
            checkBoundary({16'd0,(blueMinimum+8'd1)},2'd2);
        end

        redMinimum=8'd0;
        blueMinimum=8'd0;
        checkBoundary(24'h000000,2'd0);
        checkBoundary({8'd100,8'd0,8'd40},2'd1); // Red H = -24 exactly.
        checkBoundary({8'd100,8'd0,8'd41},2'd0); // Just below red interval.
        checkBoundary({8'd100,8'd0,8'd39},2'd1);
        checkBoundary({8'd100,8'd0,8'd0},2'd1);  // Formal pure red H = 0.
        checkBoundary({8'd100,8'd1,8'd0},2'd0);  // Positive hue/orange rejected.
        checkBoundary({8'd100,8'd0,8'd1},2'd1);  // Negative hue wraps correctly.
        checkBoundary({8'd0,8'd100,8'd150},2'd2);// Blue H = 200 exactly.
        checkBoundary({8'd0,8'd101,8'd150},2'd0);
        checkBoundary({8'd0,8'd99,8'd150},2'd2);
        checkBoundary({8'd20,8'd0,8'd120},2'd2); // Blue H = 250 exactly.
        checkBoundary({8'd21,8'd0,8'd120},2'd0);
        checkBoundary({8'd19,8'd0,8'd120},2'd2);
        checkBoundary({8'd100,8'd50,8'd50},2'd1);// S = 0.5 exactly.
        checkBoundary({8'd100,8'd51,8'd51},2'd0);
        checkBoundary({8'd50,8'd50,8'd100},2'd2);
        checkBoundary({8'd51,8'd51,8'd100},2'd0);
        checkBoundary({8'd100,8'd100,8'd0},2'd0);// Tied maximum channels.
        checkBoundary({8'd100,8'd0,8'd100},2'd0);
        checkBoundary({8'd0,8'd100,8'd100},2'd0);
        checkBoundary(24'hff0000,2'd1);          // Full signed numerator range.
        checkBoundary(24'h0000ff,2'd2);
        checkBoundary(24'h00ff00,2'd0);
        $display("PASS hsvColourGate_tb checks=%0d profiles=2 exhaustiveRGB565=131072",checks);
        $finish;
    end

    initial begin
        #1000000;
        $fatal(1,"HSV exhaustive regression timed out");
    end
endmodule
