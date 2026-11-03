`timescale 1ns/1ps
// Independent whole-row oracle: identify maximal equal-colour runs, then retain
// all pixels of runs at least two/three long. It does not copy either streaming
// predicate. Both DUTs must preserve identical metadata latency and flushing.
module horizontalRunFilter_tb;
    logic clk=0;
    always #5 clk=~clk;
    logic reset=1,in_valid=0,in_sop=0,in_eop=0;
    logic [8:0] in_x=0;
    logic [7:0] in_y=0;
    logic [1:0] in_mask=0;
    logic out_valid,out_sop,out_eop;
    logic [8:0] out_x;
    logic [7:0] out_y;
    logic [1:0] out_mask;
    logic outValid2,outSop2,outEop2;
    logic [8:0] outX2;
    logic [7:0] outY2;
    logic [1:0] outMask2;
    logic [1:0] rowPixels[0:319],expectedPixels[0:319],expectedPixels2[0:319];
    logic scoreboardActive=0;
    integer outputCount=0,rowCount=0,totalPixels=0,currentY=0;
    logic [31:0] randomState=32'h7b6e3a51;
    horizontalRunFilter #(.MIN_RUN_LENGTH(3)) dut(.*);
    horizontalRunFilter #(.MIN_RUN_LENGTH(2)) dut2(
        .clk(clk),.reset(reset),.in_valid(in_valid),.in_sop(in_sop),.in_eop(in_eop),
        .in_x(in_x),.in_y(in_y),.in_mask(in_mask),
        .out_valid(outValid2),.out_sop(outSop2),.out_eop(outEop2),
        .out_x(outX2),.out_y(outY2),.out_mask(outMask2));

    always @(posedge clk) begin
        #1;
        if(!reset) begin
            if({outValid2,outSop2,outEop2,outX2,outY2}!==
               {out_valid,out_sop,out_eop,out_x,out_y})
                $fatal(1,"RUN2/RUN3 token latency, order or flush mismatch");
            if((out_sop||out_eop)&&!out_valid)
                $fatal(1,"Frame marker asserted without output pixel");
            if(out_valid) begin
                if(!scoreboardActive) $fatal(1,"Unexpected stale output outside active row");
                if(outputCount>=320) $fatal(1,"More than 320 output pixels in row");
                if(out_x!==9'(outputCount)||out_y!==8'(currentY))
                    $fatal(1,"Coordinate/order mismatch row=%0d pixel=%0d actual=%0d,%0d",
                        rowCount,outputCount,out_x,out_y);
                if(out_mask!==expectedPixels[outputCount])
                    $fatal(1,"Run filter mismatch row=%0d x=%0d actual=%0d expected=%0d",
                        rowCount,outputCount,out_mask,expectedPixels[outputCount]);
                if(outMask2!==expectedPixels2[outputCount])
                    $fatal(1,"RUN2 mismatch row=%0d x=%0d actual=%0d expected=%0d",
                        rowCount,outputCount,outMask2,expectedPixels2[outputCount]);
                if(out_sop!==(currentY==0&&outputCount==0)||
                    out_eop!==(currentY==239&&outputCount==319))
                    $fatal(1,"SOP/EOP metadata mismatch y=%0d x=%0d",currentY,outputCount);
                outputCount++;
                totalPixels++;
            end
        end
    end

    task automatic clearRow;
        for(integer x=0;x<320;x++) rowPixels[x]=2'd0;
    endtask

    task automatic runRow(input integer rowY,input bit sourceGaps);
        integer first,last;
        begin
            currentY=rowY;
            outputCount=0;
            first=0;
            for(integer x=0;x<320;x++) begin
                expectedPixels[x]=0;expectedPixels2[x]=0;
            end
            while(first<320) begin
                last=first+1;
                while(last<320&&rowPixels[last]==rowPixels[first]) last++;
                if((rowPixels[first]==1||rowPixels[first]==2)&&(last-first>=3))
                    for(integer x=first;x<last;x++) expectedPixels[x]=rowPixels[first];
                if((rowPixels[first]==1||rowPixels[first]==2)&&(last-first>=2))
                    for(integer x=first;x<last;x++) expectedPixels2[x]=rowPixels[first];
                first=last;
            end
            scoreboardActive=1;
            for(integer x=0;x<320;x++) begin
                @(negedge clk);
                in_valid=1;in_sop=(rowY==0&&x==0);in_eop=(rowY==239&&x==319);
                in_x=9'(x);in_y=8'(rowY);in_mask=rowPixels[x];
                if(sourceGaps&&x!=319&&(x%11==0||x%23==0)) begin
                    @(negedge clk);in_valid=0;in_sop=0;in_eop=0;
                    // Arbitrary invalid bus values must never advance history.
                    in_x=9'd319;in_mask=2'd3;
                    repeat(x%3) @(negedge clk);
                end
            end
            @(negedge clk);in_valid=0;in_sop=0;in_eop=0;
            repeat(3) @(negedge clk);
            if(outputCount!=320) $fatal(1,"Row emitted %0d pixels instead of 320",outputCount);
            scoreboardActive=0;
            rowCount++;
        end
    endtask

    task automatic sendPartialTwo;
        begin
            @(negedge clk);in_valid=1;in_sop=1;in_eop=0;in_x=0;in_y=0;in_mask=1;
            @(negedge clk);in_sop=0;in_x=1;
            @(negedge clk);in_valid=0;
        end
    endtask

    initial begin
        repeat(3) @(negedge clk);
        reset=0;
        // Every start column, including truncated runs at the right edge, both
        // colours and lengths below/at/above the acceptance boundary.
        for(integer colour=1;colour<=2;colour++) begin
            for(integer lengthCase=0;lengthCase<4;lengthCase++) begin
                for(integer startX=0;startX<320;startX++) begin
                    clearRow();
                    for(integer offset=0;offset<((lengthCase==3)?17:lengthCase+1);offset++)
                        if(startX+offset<320) rowPixels[startX+offset]=2'(colour);
                    runRow(rowCount%240,(startX%7==0));
                end
            end
        end
        // Exhaust all 3^5 local foreground/background patterns against a whole
        // row oracle, separated by zeroes so independent windows cannot join.
        for(integer pattern=0;pattern<243;pattern++) begin
            integer remaining;
            clearRow();remaining=pattern;
            for(integer x=157;x<162;x++) begin
                rowPixels[x]=2'(remaining%3);remaining=remaining/3;
            end
            runRow(rowCount%240,1);
        end
        // Long runs preserve their first and last pixels, including both ends
        // of the image. Equal-length red/blue runs remain separate at a join.
        for(integer colour=1;colour<=2;colour++) begin
            for(integer x=0;x<320;x++) rowPixels[x]=2'(colour);
            runRow(239,1);
        end
        for(integer x=0;x<320;x++) rowPixels[x]=(x<160)?2'd1:2'd2;
        runRow(0,1);
        // Invalid/ambiguous mask 3 is background, even for a complete row.
        for(integer x=0;x<320;x++) rowPixels[x]=2'd3;
        runRow(239,0);
        // Deterministic mixed run lengths exercise densely alternating colours.
        for(integer row=0;row<32;row++) begin
            for(integer x=0;x<320;x++) begin
                randomState={randomState[30:0],randomState[31]^randomState[21]^randomState[1]^randomState[0]};
                rowPixels[x]=randomState[1:0];
            end
            runRow(rowCount%240,1);
        end
        // Two pending pixels from an incomplete frame must be discarded by a
        // new SOP, and by synchronous reset, without escaping later as stale data.
        sendPartialTwo();
        clearRow();rowPixels[2]=2'd2;rowPixels[3]=2'd2;rowPixels[4]=2'd2;
        runRow(0,1);
        sendPartialTwo();
        reset=1;
        repeat(2) @(negedge clk);
        if(out_valid||out_sop||out_eop||outValid2||outSop2||outEop2)
            $fatal(1,"Reset did not discard pending pixels");
        reset=0;
        clearRow();rowPixels[317]=2'd1;rowPixels[318]=2'd1;rowPixels[319]=2'd1;
        runRow(239,1);
        $display("PASS horizontalRunFilter_tb rows=%0d orderedPixels=%0d exhaustiveLocalPatterns=243 minimumRuns=2,3 equalTokenLatency=1",rowCount,totalPixels);
        $finish;
    end
    initial begin
        #30000000;
        $fatal(1,"Horizontal run filter regression timed out");
    end
endmodule
