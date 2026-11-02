`timescale 1ns/1ps
module colourSampler_tb;
    import candidate_pkg::*;
    logic clk=0,reset=1,sof=0,pixelValid=0,eop=0,collectEnable=1,roiValid=1;
    always #10 clk=~clk;
    logic [8:0] x=0;
    logic [7:0] y=0;
    logic [23:0] rgb=0;
    logic [1:0] orientation=0;
    candidate_t redBox,blueBox,sampledRedBox,sampledBlueBox;
    logic frameSampleGood;
    logic [7:0] redMinimum,blueMinimum;
    logic [16:0] redSamples,blueSamples;
    colourSampler dut(.*);
    task automatic scene(input integer mode);
        @(negedge clk);sof=1;
        @(negedge clk);sof=0;
        for(int py=0;py<130;py++) for(int px=0;px<170;px++) begin
            x=px;y=py;pixelValid=1;rgb=0;
            if(px>=20&&px<=119&&py>=20&&py<=119)
                rgb=mode==1 ? 24'h300a0a : mode==2 ? 24'h0a0808 : 24'h781410;
            if(px>=130&&px<=159&&py>=20&&py<=119)
                rgb=mode==1 ? 24'h0a0a1c : 24'h0a1440;
            if(mode==3&&px==30&&py==60)rgb=24'hffffff;
            if(mode==4&&px>=20&&px<=119&&py>=20&&py<=119)rgb=24'hff1410;
            if(mode==5&&px>=130&&px<=159&&py>=20&&py<=119)rgb=24'h0a14ff;
            if(mode==6&&px>=130&&px<=159&&py>=20&&py<=119)
                rgb=py<70?24'h081429:24'h081431;
            @(negedge clk);
        end
        pixelValid=0;eop=1;
        @(negedge clk);eop=0;
    endtask
    initial begin
        redBox='0;blueBox='0;
        redBox.valid=1;redBox.xmin=20;redBox.xmax=119;redBox.ymin=20;redBox.ymax=119;
        blueBox.valid=1;blueBox.xmin=130;blueBox.xmax=159;blueBox.ymin=20;blueBox.ymax=119;
        repeat(3)@(negedge clk);reset=0;
        scene(0);
        if(!frameSampleGood || redSamples!=400 || blueSamples!=1080 || redMinimum!=60 || blueMinimum!=32)
            $fatal(1,"inset raw RGB statistics r=%0d b=%0d",redSamples,blueSamples);
        scene(1);
        if(!frameSampleGood || redMinimum!=24 || blueMinimum!=14)
            $fatal(1,"samples below old segmentation threshold must still be collected");
        scene(2);if(frameSampleGood)$fatal(1,"dark reference accepted");
        scene(3);if(frameSampleGood)$fatal(1,"white pollution accepted");
        scene(4);if(frameSampleGood)$fatal(1,"clipped dominant red accepted");
        scene(5);if(frameSampleGood)$fatal(1,"clipped dominant blue accepted");
        scene(6);if(!frameSampleGood||blueMinimum!=20)
            $fatal(1,"V floor must use raw darkest validated reference, not midrange");
        orientation=1;scene(0);
        if(!frameSampleGood || redSamples!=400)$fatal(1,"rotated inset sample");
        collectEnable=0;scene(0);if(frameSampleGood)$fatal(1,"disabled collection accepted");
        collectEnable=1;roiValid=0;scene(0);if(frameSampleGood)$fatal(1,"invalid pairing accepted");
        roiValid=1;orientation=0;redBox.xmax=29;redBox.ymax=29;
        scene(0);if(frameSampleGood || redSamples>=16)$fatal(1,"insufficient sample size accepted");
        $display("PASS colourSampler_tb");$finish;
    end
    initial begin #10000000;$fatal(1,"timeout colourSampler_tb");end
endmodule
