`timescale 1ns/1ps
module memberBVgaHsv_tb;
    logic clk=0,reset=1,start=0,ready,valid;
    logic [23:0] rgb=0;
    logic [8:0] hue;
    logic [7:0] saturation,value;
    int checked=0,maxLatency=0;
    always #5 clk=~clk;
    memberBVgaHsv dut(.*);
    task automatic check(input int r,g,b);
        int mx,mn,d,expectedHue,expectedSat,latency;
        mx=r;if(g>mx)mx=g;if(b>mx)mx=b;
        mn=r;if(g<mn)mn=g;if(b<mn)mn=b;
        d=mx-mn;expectedHue=0;expectedSat=0;
        if(d!=0)begin
            if(mx==r)expectedHue=(60*(g-b))/d;
            else if(mx==g)expectedHue=120+(60*(b-r))/d;
            else expectedHue=240+(60*(r-g))/d;
            if(expectedHue<0)expectedHue+=360;
            if(expectedHue>=360)expectedHue-=360;
            expectedSat=(255*d)/mx;
        end
        @(negedge clk);if(!ready)$fatal(1,"FAIL converter not ready");rgb={8'(r),8'(g),8'(b)};start=1;
        @(posedge clk);#1;latency=0;
        @(negedge clk);start=0;rgb=24'hbad123;
        while(!valid&&latency<40)begin @(posedge clk);#1;latency++;end
        if(!valid||hue!=expectedHue||saturation!=expectedSat||value!=mx)
            $fatal(1,"FAIL HSV rgb%0d,%0d,%0d expected%0d,%0d,%0d got%0d,%0d,%0d latency%0d",r,g,b,expectedHue,expectedSat,mx,hue,saturation,value,latency);
        if(latency>maxLatency)maxLatency=latency;
        checked++;
        @(posedge clk);#1;if(valid)$fatal(1,"FAIL HSV valid did not pulse");
    endtask
    initial begin
        repeat(3)@(negedge clk);reset=0;
        for(int grey=0;grey<256;grey++)check(grey,grey,grey);
        // Every representable RGB565 code; input expansion matches camera RGB.
        for(int pixelCode=0;pixelCode<65536;pixelCode++)
            check((((pixelCode>>11)&31)<<3)|(((pixelCode>>11)&31)>>2),
                  (((pixelCode>>5)&63)<<2)|(((pixelCode>>5)&63)>>4),
                  ((pixelCode&31)<<3)|((pixelCode&31)>>2));
        $display("PASS memberBVgaHsv_tb: %0d exact conversions including RGB565 full domain, max latency%0d",checked,maxLatency);
        $finish;
    end
    initial begin #30000000;$fatal(1,"FAIL HSV timeout");end
endmodule
