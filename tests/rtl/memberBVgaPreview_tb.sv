`timescale 1ns/1ps
// Artifact-only RTL replay of explicitly supplied RGB/metadata. The output is
// a display preview, not a new camera capture or physical VGA acceptance.
module memberBVgaPreview_tb;
    logic clk=0,reset=1,showCandidates=1,showCentre=1;
    logic [3071:0] debugWords=0;
    logic [29:0] inData=0,outData;
    logic inSop=0,inEop=0,inValid=0,inReady,outSop,outEop,outValid,outReady=1;
    logic [29:0] pixels[0:307199];
    logic [31:0] metadata[0:95];
    string vectors;
    integer outputFile,outputFrame=0,written=0;
    always #20 clk=~clk;
    memberBVgaOverlay dut(.*);
    always @(posedge clk)if(!reset&&outValid&&outReady)begin
        if(outSop)outputFrame++;
        if(outputFrame==3)begin $fwrite(outputFile,"%08x\n",outData);written++;end
    end
    initial begin
        if(!$value$plusargs("VECTORS=%s",vectors))$fatal(1,"FAIL preview requires explicitly sourced inputs");
        $readmemh({vectors,"/display_rgb.hex"},pixels);
        $readmemh({vectors,"/debug_words.hex"},metadata);
        for(int i=0;i<96;i++)debugWords[i*32+:32]=metadata[i];
        outputFile=$fopen({vectors,"/rendered_rgb.hex"},"w");
        if(outputFile==0)$fatal(1,"FAIL cannot open preview output");
        repeat(4)@(negedge clk);reset=0;
        for(int frame=0;frame<3;frame++)begin
            for(int i=0;i<307200;i++)begin
                @(negedge clk);inData=pixels[i];inValid=1;inSop=i==0;inEop=i==307199;
                @(posedge clk);while(!inReady)@(posedge clk);
            end
            @(negedge clk);inValid=0;inSop=0;inEop=0;
            repeat(1000)@(negedge clk);
        end
        $fclose(outputFile);
        if(written!=307200)$fatal(1,"FAIL preview pixel count %0d",written);
        $display("PASS memberBVgaPreview_tb: 307200 rendered pixels; recorded-input RTL preview only");
        $finish;
    end
    initial begin #50000000;$fatal(1,"FAIL preview timeout");end
endmodule
