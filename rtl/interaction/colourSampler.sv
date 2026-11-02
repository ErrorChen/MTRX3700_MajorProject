// Raw RGB samples from paired red-card/blue-strip regions, frozen at SOF.
// Colour masks never filter these samples. The reader must subsequently verify
// the same frame's card geometry before accepting completed statistics.
module colourSampler (
    input logic clk,reset,sof,pixelValid,eop,collectEnable,roiValid,
    input logic [8:0] x,
    input logic [7:0] y,
    input logic [23:0] rgb,
    input logic [1:0] orientation,
    input candidate_pkg::candidate_t redBox,blueBox,
    output logic frameSampleGood,
    output logic [7:0] redMinimum,blueMinimum,
    output logic [16:0] redSamples,blueSamples,
    output candidate_pkg::candidate_t sampledRedBox,sampledBlueBox
);
    import candidate_pkg::*;
    candidate_t heldRed,heldBlue;
    logic collecting;
    logic [1:0] heldOrientation;
    logic [16:0] redCount,blueCount;
    logic [7:0] redLow,redHigh,blueLow,blueHigh,redOther,blueOther;
    logic [9:0] w,h,u,v;
    logic redHit,blueHit;
    logic [7:0] r,g,b;
    always_comb begin
        r=rgb[23:16];g=rgb[15:8];b=rgb[7:0];
        w=heldOrientation[0]?10'(heldRed.ymax-heldRed.ymin+1):10'(heldRed.xmax-heldRed.xmin+1);
        h=heldOrientation[0]?10'(heldRed.xmax-heldRed.xmin+1):10'(heldRed.ymax-heldRed.ymin+1);
        case(heldOrientation)
            0:begin u=10'(x)-10'(heldRed.xmin);v=10'(y)-10'(heldRed.ymin);end
            1:begin u=10'(y)-10'(heldRed.ymin);v=10'(heldRed.xmax)-10'(x);end
            2:begin u=10'(heldRed.xmax)-10'(x);v=10'(heldRed.ymax)-10'(y);end
            default:begin u=10'(heldRed.ymax)-10'(y);v=10'(x)-10'(heldRed.xmin);end
        endcase
        redHit=x>=heldRed.xmin&&x<=heldRed.xmax&&y>=heldRed.ymin&&y<=heldRed.ymax&&
            u*100>=w*8&&u*100<w*18&&v*10>=h*3&&v*10<h*7;
        blueHit=x>=heldBlue.xmin&&x<=heldBlue.xmax&&y>=heldBlue.ymin&&y<=heldBlue.ymax&&
            (10'(x)-10'(heldBlue.xmin))*5>=10'(heldBlue.xmax-heldBlue.xmin+1)&&
            (10'(x)-10'(heldBlue.xmin))*5<10'(heldBlue.xmax-heldBlue.xmin+1)*4&&
            (10'(y)-10'(heldBlue.ymin))*5>=10'(heldBlue.ymax-heldBlue.ymin+1)&&
            (10'(y)-10'(heldBlue.ymin))*5<10'(heldBlue.ymax-heldBlue.ymin+1)*4;
    end
    always_ff @(posedge clk) begin
        if(reset) begin
            heldRed<='0;heldBlue<='0;collecting<=0;heldOrientation<=0;
            redCount<=0;blueCount<=0;redLow<=255;blueLow<=255;redHigh<=0;blueHigh<=0;
            redOther<=0;blueOther<=0;frameSampleGood<=0;redMinimum<=64;blueMinimum<=32;
            redSamples<=0;blueSamples<=0;sampledRedBox<='0;sampledBlueBox<='0;
        end else begin
            if(sof) begin
                collecting<=collectEnable&&roiValid;
                heldRed<=redBox;heldBlue<=blueBox;heldOrientation<=orientation;
                redCount<=0;blueCount<=0;redLow<=255;blueLow<=255;redHigh<=0;blueHigh<=0;
                redOther<=0;blueOther<=0;
            end
            if(pixelValid&&collecting) begin
                if(redHit) begin
                    redCount<=redCount+17'd1;
                    if(r<redLow)redLow<=r;if(r>redHigh)redHigh<=r;
                    if(g>redOther||b>redOther)redOther<=g>b?g:b;
                end
                if(blueHit) begin
                    blueCount<=blueCount+17'd1;
                    if(b<blueLow)blueLow<=b;if(b>blueHigh)blueHigh<=b;
                    if(g>blueOther||r>blueOther)blueOther<=g>r?g:r;
                end
            end
            // References are inset: the bottom-right EOP cannot be a sample.
            if(eop) begin
                frameSampleGood<=collecting&&redCount>=16&&blueCount>=16&&
                    redLow>=32&&blueLow>=24&&
                    {1'b0,redLow}>{1'b0,redOther}+9'd8&&
                    {1'b0,blueLow}>{1'b0,blueOther}+9'd8&&
                    redHigh-redLow<=80&&blueHigh-blueLow<=80&&redOther<224&&blueOther<224;
                // Midrange/2 adjusts the HSV value floors only. Hue/saturation
                // and the independent white threshold remain unchanged.
                redMinimum<=8'(({1'b0,redLow}+{1'b0,redHigh})>>2);
                blueMinimum<=8'(({1'b0,blueLow}+{1'b0,blueHigh})>>2);
                redSamples<=redCount;blueSamples<=blueCount;
                sampledRedBox<=heldRed;sampledBlueBox<=heldBlue;
            end
        end
    end
endmodule
