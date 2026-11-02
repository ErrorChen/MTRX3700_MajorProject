// Accepted digit labels for the camera_display ROTATE_CCW_90 picture: the portrait
// occupies display x=140..499 and scales native u=y,v=319-x by 3/2. Only actual
// accepted markers are drawn. debugWords must already be delivered as one held
// coherent transaction into this VGA clock domain by the top-level CDC.
// A one-entry elastic output register preserves all Avalon-ST payload on stalls.
module memberBVgaLabels #(
    // Additional protection if camera/debug updates stop entirely. This is a
    // display-refresh budget, not an assertion about camera pipeline latency.
    parameter int MAX_HOLD_FRAMES=10
) (
    input logic clk, reset,
    input logic [3071:0] debugWords,
    input logic [29:0] inData,
    input logic inSop,inEop,inValid,
    output logic inReady,
    output logic [29:0] outData,
    output logic outSop,outEop,outValid,
    input logic outReady
);
    logic [31:0] markerWords[0:63];
    logic [15:0] heldFrameId,heldConfigVersion;
    logic haveFrame,heldFrameGood;
    logic [7:0] unchangedFrames;
    logic [9:0] rasterX,pixelX;
    logic [8:0] rasterY,pixelY;
    logic [29:0] renderedData;
    logic [31:0] markerHeader,xWord,yWord;
    logic [6:0] digitSegments;
    logic digitInk,labelRegion,typeInk;
    integer uMin,uMax,vMin,vMax,labelX,labelY,glyphX,glyphY;
    logic sourceFrameGood;
    logic [31:0] captureAge;

    function automatic logic [6:0] segmentsForDigit(input logic [3:0] digit);
        case(digit)
            1:segmentsForDigit=7'b0000110;
            2:segmentsForDigit=7'b1011011;
            3:segmentsForDigit=7'b1001111;
            4:segmentsForDigit=7'b1100110;
            5:segmentsForDigit=7'b1101101;
            6:segmentsForDigit=7'b1111101;
            default:segmentsForDigit=0;
        endcase
    endfunction
    assign inReady=!outValid || outReady;
    always_comb begin
        captureAge=debugWords[2*32+:32]-debugWords[4*32+:32];
        sourceFrameGood=debugWords[91*32] && !captureAge[31] && captureAge<=32'd150000;
        pixelX=inSop?10'd0:rasterX;
        pixelY=inSop?9'd0:rasterY;
        renderedData=inData;
        markerHeader=0;xWord=0;yWord=0;digitSegments=0;
        digitInk=0;labelRegion=0;typeInk=0;
        uMin=0;uMax=0;vMin=0;vMax=0;
        labelX=0;labelY=0;glyphX=0;glyphY=0;
        if(heldFrameGood && haveFrame && pixelX>=140 && pixelX<500) begin
            for(int markerIndex=0;markerIndex<16;markerIndex++) begin
                markerHeader=markerWords[markerIndex*4];
                xWord=markerWords[markerIndex*4+1];
                yWord=markerWords[markerIndex*4+2];
                uMin=int'(yWord[23:16]);uMax=int'(yWord[7:0]);
                vMin=319-int'(xWord[8:0]);vMax=319-int'(xWord[24:16]);
                digitInk=0;labelRegion=0;
                if(markerHeader[31] && markerHeader[27:24]>=1 && markerHeader[27:24]<=6 &&
                    uMin<=uMax && vMin<=vMax && uMax<240 && vMax<320 && vMin>=0) begin
                    labelX=140+(uMin*3)/2+3;labelY=(vMin*3)/2+3;
                    glyphX=int'(pixelX)-labelX;glyphY=int'(pixelY)-labelY;
                    labelRegion=glyphX>=0 && glyphX<16 && glyphY>=0 && glyphY<12;
                    digitSegments=segmentsForDigit(markerHeader[27:24]);
                    if(labelRegion) begin
                        // The type letter is independent of the recognised
                        // numeral. Red/blue backgrounds provide a second cue.
                        typeInk=(glyphX==0&&glyphY>=1&&glyphY<=10)||
                            ((glyphY==0||glyphY==5)&&glyphX>=0&&glyphX<=4)||
                            (glyphX==5&&glyphY>=1&&glyphY<=4);
                        if(markerHeader[30])typeInk=typeInk||
                            (glyphY==11&&glyphX<=4&&glyphX>=0)||(glyphX==5&&glyphY>=6&&glyphY<=10);
                        else typeInk=typeInk||(glyphY>=6&&glyphY<=10&&glyphX==glyphY-5);
                        digitInk=(digitSegments[0]&&glyphY==0&&glyphX>=9&&glyphX<=14)||
                            (digitSegments[1]&&glyphX==15&&glyphY>=1&&glyphY<=4)||
                            (digitSegments[2]&&glyphX==15&&glyphY>=6&&glyphY<=10)||
                            (digitSegments[3]&&glyphY==11&&glyphX>=9&&glyphX<=14)||
                            (digitSegments[4]&&glyphX==8&&glyphY>=6&&glyphY<=10)||
                            (digitSegments[5]&&glyphX==8&&glyphY>=1&&glyphY<=4)||
                            (digitSegments[6]&&glyphY==5&&glyphX>=9&&glyphX<=14);
                        renderedData=(digitInk||typeInk)?{10'h3ff,10'h3ff,10'h3ff}:
                            markerHeader[30]?{10'd0,10'd128,10'd512}:{10'd512,10'd0,10'd0};
                    end
                end
            end
        end
    end

    always_ff @(posedge clk) begin
        if(reset) begin
            outData<=0;outSop<=0;outEop<=0;outValid<=0;
            rasterX<=0;rasterY<=0;heldFrameId<=0;heldConfigVersion<=0;
            haveFrame<=0;heldFrameGood<=0;unchangedFrames<=0;
            for(int i=0;i<64;i++) markerWords[i]<=0;
        end else if(inReady) begin
            outValid<=inValid;
            if(inValid) begin
                outData<=renderedData;outSop<=inSop;outEop<=inEop;
                if(inSop) begin
                    rasterX<=1;rasterY<=0;
                    for(int i=0;i<64;i++) markerWords[i]<=debugWords[(24+i)*32+:32];
                    heldFrameId<=debugWords[3*32+:16];
                    heldConfigVersion<=debugWords[6*32+:16];haveFrame<=1;
                    if(haveFrame && heldFrameId==debugWords[3*32+:16] && heldConfigVersion==debugWords[6*32+:16]) begin
                        if(unchangedFrames!=255)unchangedFrames<=unchangedFrames+8'd1;
                        heldFrameGood<=sourceFrameGood && unchangedFrames<MAX_HOLD_FRAMES-1;
                    end else begin unchangedFrames<=0;heldFrameGood<=sourceFrameGood;end
                end else if(rasterX==639) begin
                    rasterX<=0;
                    rasterY<=rasterY==479?9'd0:rasterY+9'd1;
                end else rasterX<=rasterX+10'd1;
            end
        end
    end
endmodule
