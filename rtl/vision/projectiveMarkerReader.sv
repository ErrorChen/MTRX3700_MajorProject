// Same-frame quadrilateral rectification and pixel-derived marker decoding.
// CLOCK_50 only; both RAM inputs have one synchronous read cycle of latency.
// Corner coordinates are found from RAW colour foreground within each candidate.
// A 32x40 canonical grid uses an exact integer homography. Coefficients share a
// denominator; each source x/y quotient is calculated in nine serial bit steps,
// rather than inferring a wide combinational division circuit. No grid position
// or candidate index supplies a digit answer.
module projectiveMarkerReader #(
    parameter int MIN_EDGE_PIXELS=24,
    parameter int MIN_QUAD_AREA=400
) (
    input logic clk,reset,start,
    input candidate_pkg::candidate_array_t redCandidates,blueCandidates,
    input logic [1:0] orientationProfile,
    output logic busy,done,
    output logic [16:0] readAddress,
    input logic readWhite,readColour,
    output vision_pkg::markerArray_t markers,
    output logic [4:0] acceptedCount
);
    import candidate_pkg::*;
    import vision_pkg::*;
    typedef enum logic [4:0] {
        IDLE,SETUP,SCAN_INIT,SCAN_WAIT,SCAN_SAMPLE,CORNER_PREP,GEOMETRY,
        HOMO_DELTAS,HOMO_PRODUCTS,HOMO_SIGN,HOMO_COEFF,GRID_NUM,GRID_PREP,
        DIVIDE,MAP_ADDRESS,GRID_WAIT,GRID_SAMPLE,DECIDE,NEXT,MULTIPLY_WAIT,GRID_INIT
    } state_t;
    state_t state;
    candidate_array_t heldRed,heldBlue;
    candidate_t box;
    logic [3:0] index;
    logic [1:0] orientation;
    logic [8:0] scanX;
    logic [7:0] scanY;
    logic [9:0] boxWidth,boxHeight;
    logic signed [20:0] scorePlus,scoreMinus,minPlus,maxPlus,minMinus,maxMinus;
    logic [8:0] relativeX;
    logic [7:0] relativeY;
    logic [18:0] scaledX,scaledY;
    logic [8:0] cornerX[0:3];
    logic [7:0] cornerY[0:3];
    // Signed half-pixel units. Raw contour corners are expanded by half a pixel
    // towards their native quadrant to represent the coloured rectangle edges.
    logic signed [10:0] pointX[0:3],pointY[0:3];
    logic [16:0] foregroundCount;
    logic geometryRejected,mapRejected;
    // Native x spans 0..319 and y 0..239. In half-pixel units a difference
    // therefore fits signed 11 bits (-640..640). Never promote geometry to
    // int32 multiplication: that consumed 74 DSPs in the first full fitter run.
    logic signed [24:0] areaTwice;
    logic signed [10:0] edgeDx[0:3],edgeDy[0:3];
    logic signed [22:0] crossProduct[0:3],areaTerm[0:3];
    logic [22:0] edgeSquared[0:3];
    logic quadrilateralGood;
    logic signed [11:0] dx1,dx2,dx3,dy1,dy2,dy3;
    logic signed [24:0] determinant,gNumerator,hNumerator,dNorm,gNorm,hNorm;
    logic signed [35:0] ax,bx,cx,ay,by,cy;
    logic [3:0] multiplyOperation;
    logic signed [24:0] multiplyA;
    logic signed [11:0] multiplyB;
    logic signed [36:0] multiplyResult,firstProduct;
    logic multiplyDone;
    logic [4:0] gridX;
    logic [5:0] gridY;
    logic signed [9:0] gridU,gridV;
    logic signed [47:0] numeratorX,numeratorY,denominator;
    logic signed [47:0] rowNumeratorX,rowNumeratorY,rowDenominator;
    logic [47:0] remainderX,remainderY,divisionDenominator,shiftedDenominator;
    logic [8:0] quotientX,quotientY;
    logic [3:0] divisionBit;
    logic [7:0] strokeProjection[0:6];
    logic [5:0] anchorColumns;
    logic [4:0] anchorRows;
    logic [5:0] anchorCount,holeUpperWhite,holeLowerWhite;
    logic [6:0] segmentBits;
    logic uncertain,strongEvidence,shapeGood,highResolutionQuad;
    logic [3:0] decodedDigit;
    marker_t decision;
    projectiveSerialMultiply coefficientMultiplier(.clk(clk),.reset(reset),
        .start(state==HOMO_PRODUCTS),.operandA(multiplyA),.operandB(multiplyB),
        .result(multiplyResult),.done(multiplyDone));

    function automatic integer population(input logic [7:0] value);
        integer total;
        begin total=0;for(int bitIndex=0;bitIndex<8;bitIndex++)total=total+int'(value[bitIndex]);population=total;end
    endfunction

    always_comb begin
        boxWidth={1'b0,box.xmax}-{1'b0,box.xmin}+10'd1;
        boxHeight={2'b0,box.ymax}-{2'b0,box.ymin}+10'd1;
        // Products normalise x/y by the candidate dimensions without division.
        relativeX=scanX-box.xmin;relativeY=scanY-box.ymin;
        scaledX=relativeX*boxHeight;scaledY=relativeY*boxWidth;
        scorePlus=$signed({2'b0,scaledX})+$signed({2'b0,scaledY});
        scoreMinus=$signed({2'b0,scaledX})-$signed({2'b0,scaledY});
        areaTwice=0;quadrilateralGood=foregroundCount>=32;highResolutionQuad=1;
        for(int i=0;i<4;i++)begin
            edgeDx[i]=pointX[(i+1)%4]-pointX[i];
            edgeDy[i]=pointY[(i+1)%4]-pointY[i];
            areaTerm[i]=pointX[i]*pointY[(i+1)%4]-pointY[i]*pointX[(i+1)%4];
            areaTwice=areaTwice+areaTerm[i];
        end
        for(int i=0;i<4;i++)begin
            crossProduct[i]=edgeDx[i]*edgeDy[(i+1)%4]-edgeDy[i]*edgeDx[(i+1)%4];
            edgeSquared[i]=edgeDx[i]*edgeDx[i]+edgeDy[i]*edgeDy[i];
            if(crossProduct[i]<=0 || edgeSquared[i] < 23'(4*MIN_EDGE_PIXELS*MIN_EDGE_PIXELS))
                quadrilateralGood=0;
            if(edgeSquared[i]<23'd6400)highResolutionQuad=0;
        end
        // point coordinates are doubled, so twice-area is eight times pixel area.
        if(areaTwice<8*MIN_QUAD_AREA)quadrilateralGood=0;
        gridU=$signed({1'b0,gridX,1'b1})*10'sd5;
        gridV=$signed({1'b0,gridY,1'b1})*10'sd4;
        // One signed shift/add multiplier is time-shared across determinant and
        // all six coefficients. These values change once per candidate only.
        multiplyA=0;multiplyB=0;
        case(multiplyOperation)
            0:begin multiplyA=dx1;multiplyB=dy2;end
            1:begin multiplyA=dx2;multiplyB=dy1;end
            2:begin multiplyA=dx3;multiplyB=dy2;end
            3:begin multiplyA=dx2;multiplyB=dy3;end
            4:begin multiplyA=dx1;multiplyB=dy3;end
            5:begin multiplyA=dx3;multiplyB=dy1;end
            6:begin multiplyA=dNorm;multiplyB=pointX[1]-pointX[0];end
            7:begin multiplyA=gNorm;multiplyB=pointX[1];end
            8:begin multiplyA=dNorm;multiplyB=pointX[3]-pointX[0];end
            9:begin multiplyA=hNorm;multiplyB=pointX[3];end
            10:begin multiplyA=dNorm;multiplyB=pointX[0];end
            11:begin multiplyA=dNorm;multiplyB=pointY[1]-pointY[0];end
            12:begin multiplyA=gNorm;multiplyB=pointY[1];end
            13:begin multiplyA=dNorm;multiplyB=pointY[3]-pointY[0];end
            14:begin multiplyA=hNorm;multiplyB=pointY[3];end
            default:begin multiplyA=dNorm;multiplyB=pointY[0];end
        endcase
        if(state==SCAN_INIT||state==SCAN_WAIT||state==SCAN_SAMPLE)
            readAddress=17'(scanY)*17'd320+17'(scanX);
        else readAddress=17'(quotientY)*17'd320+17'(quotientX);
        segmentBits=0;uncertain=0;
        // A two-pixel stroke can classify consistently yet does not justify the
        // strongest quality tier. Every quadrilateral edge must span >=40 px.
        strongEvidence=anchorCount>=4&&highResolutionQuad;
        for(int i=0;i<7;i++)begin
            // Horizontal strokes cover eight independent canonical columns;
            // vertical strokes cover seven rows. Middle evidence is rejected.
            if(population(strokeProjection[i])>=5)begin
                segmentBits[i]=1;
                if(population(strokeProjection[i]) < ((i==0||i==3||i==6)?7:6))strongEvidence=0;
            end else if(population(strokeProjection[i])>2)uncertain=1;
        end
        shapeGood=anchorCount>=3&&population({2'b0,anchorColumns})>=2&&population({3'b0,anchorRows})>=2&&
            holeUpperWhite<=4&&holeLowerWhite<=4;
        decodedDigit=15;
        case(segmentBits)
            7'b0000110:decodedDigit=1;
            7'b1011011:decodedDigit=2;
            7'b1001111:decodedDigit=3;
            7'b1100110:decodedDigit=4;
            7'b1101101:decodedDigit=5;
            7'b1111101:decodedDigit=6;
            default:decodedDigit=15;
        endcase
        decision='0;decision.isBlue=index[3];decision.digit=15;
        decision.xMin=box.xmin;decision.xMax=box.xmax;decision.yMin=box.ymin;decision.yMax=box.ymax;
        decision.orientation=orientation;decision.segments=segmentBits;
        if(geometryRejected)decision.reason=1;
        else if(mapRejected)decision.reason=6;
        else if(uncertain)decision.reason=3;
        else if(!shapeGood)decision.reason=4;
        else if(decodedDigit==15||(!index[3]&&decodedDigit>2))decision.reason=5;
        else begin decision.accepted=1;decision.digit=decodedDigit;decision.quality=strongEvidence?8'd255:8'd192;end
    end
    assign busy=state!=IDLE;

    always_ff @(posedge clk)begin
        if(reset)begin
            state<=IDLE;done<=0;markers<='0;acceptedCount<=0;
            heldRed<='0;heldBlue<='0;box<='0;index<=0;orientation<=0;
            scanX<=0;scanY<=0;foregroundCount<=0;geometryRejected<=0;mapRejected<=0;
            minPlus<=0;maxPlus<=0;minMinus<=0;maxMinus<=0;
            dx1<=0;dx2<=0;dx3<=0;dy1<=0;dy2<=0;dy3<=0;
            determinant<=0;gNumerator<=0;hNumerator<=0;dNorm<=0;gNorm<=0;hNorm<=0;
            ax<=0;bx<=0;cx<=0;ay<=0;by<=0;cy<=0;
            multiplyOperation<=0;firstProduct<=0;
            gridX<=0;gridY<=0;numeratorX<=0;numeratorY<=0;denominator<=0;
            rowNumeratorX<=0;rowNumeratorY<=0;rowDenominator<=0;
            remainderX<=0;remainderY<=0;divisionDenominator<=0;shiftedDenominator<=0;divisionBit<=0;quotientX<=0;quotientY<=0;
            anchorColumns<=0;anchorRows<=0;anchorCount<=0;holeUpperWhite<=0;holeLowerWhite<=0;
            for(int i=0;i<4;i++)begin cornerX[i]<=0;cornerY[i]<=0;pointX[i]<=0;pointY[i]<=0;end
            for(int i=0;i<7;i++)strokeProjection[i]<=0;
        end else begin
            done<=0;
            case(state)
                IDLE:if(start)begin
                    heldRed<=redCandidates;heldBlue<=blueCandidates;orientation<=orientationProfile;
                    index<=0;markers<='0;acceptedCount<=0;state<=SETUP;
                end
                SETUP:begin
                    box<=index[3]?heldBlue[index[2:0]]:heldRed[index[2:0]];
                    // Both sentinels are representable signed 21-bit literals;
                    // valid native-image scores lie strictly inside this range.
                    minPlus<=21'sd1048575;maxPlus<=-21'sd1048575;
                    minMinus<=21'sd1048575;maxMinus<=-21'sd1048575;
                    foregroundCount<=0;geometryRejected<=0;mapRejected<=0;
                    anchorColumns<=0;anchorRows<=0;anchorCount<=0;holeUpperWhite<=0;holeLowerWhite<=0;
                    for(int i=0;i<4;i++)begin cornerX[i]<=0;cornerY[i]<=0;end
                    for(int i=0;i<7;i++)strokeProjection[i]<=0;
                    state<=SCAN_INIT;
                end
                SCAN_INIT:begin
                    scanX<=box.xmin;scanY<=box.ymin;
                    if(!box.valid||box.xmin>box.xmax||box.ymin>box.ymax||box.xmax>=320||box.ymax>=240||
                        boxWidth<MIN_EDGE_PIXELS||boxHeight<MIN_EDGE_PIXELS)begin geometryRejected<=1;state<=DECIDE;end
                    else state<=SCAN_WAIT;
                end
                SCAN_WAIT:state<=SCAN_SAMPLE;
                SCAN_SAMPLE:begin
                    if(readColour)begin
                        foregroundCount<=foregroundCount+17'd1;
                        if(scorePlus<minPlus)begin minPlus<=scorePlus;cornerX[0]<=scanX;cornerY[0]<=scanY;end
                        if(scoreMinus>maxMinus)begin maxMinus<=scoreMinus;cornerX[1]<=scanX;cornerY[1]<=scanY;end
                        if(scorePlus>maxPlus)begin maxPlus<=scorePlus;cornerX[2]<=scanX;cornerY[2]<=scanY;end
                        if(scoreMinus<minMinus)begin minMinus<=scoreMinus;cornerX[3]<=scanX;cornerY[3]<=scanY;end
                    end
                    if(scanX==box.xmax)begin
                        scanX<=box.xmin;
                        if(scanY==box.ymax)state<=CORNER_PREP;
                        else begin scanY<=scanY+8'd1;state<=SCAN_WAIT;end
                    end else begin scanX<=scanX+9'd1;state<=SCAN_WAIT;end
                end
                CORNER_PREP:begin
                    for(int i=0;i<4;i++)begin
                        pointX[i]<=11'({1'b0,cornerX[(i+int'(orientation))%4],1'b0})+
                            (((i+int'(orientation))%4==0||(i+int'(orientation))%4==3)?-11'sd1:11'sd1);
                        pointY[i]<=11'({2'b0,cornerY[(i+int'(orientation))%4],1'b0})+
                            (((i+int'(orientation))%4<2)?-11'sd1:11'sd1);
                    end
                    state<=GEOMETRY;
                end
                GEOMETRY:if(!quadrilateralGood)begin geometryRejected<=1;state<=DECIDE;end
                    else state<=HOMO_DELTAS;
                HOMO_DELTAS:begin
                    dx1<=pointX[1]-pointX[2];dx2<=pointX[3]-pointX[2];dx3<=pointX[0]-pointX[1]+pointX[2]-pointX[3];
                    dy1<=pointY[1]-pointY[2];dy2<=pointY[3]-pointY[2];dy3<=pointY[0]-pointY[1]+pointY[2]-pointY[3];
                    multiplyOperation<=0;state<=HOMO_PRODUCTS;
                end
                HOMO_PRODUCTS:state<=MULTIPLY_WAIT;
                MULTIPLY_WAIT:if(multiplyDone)begin
                    case(multiplyOperation)
                        0,2,4,6,8,11,13:firstProduct<=multiplyResult;
                        1:determinant<=25'(firstProduct-multiplyResult);
                        3:gNumerator<=25'(firstProduct-multiplyResult);
                        5:hNumerator<=25'(firstProduct-multiplyResult);
                        7:ax<=36'(firstProduct+multiplyResult);
                        9:bx<=36'(firstProduct+multiplyResult);
                        10:cx<=36'(multiplyResult);
                        12:ay<=36'(firstProduct+multiplyResult);
                        14:by<=36'(firstProduct+multiplyResult);
                        15:cy<=36'(multiplyResult);
                        default:;
                    endcase
                    if(multiplyOperation==5)state<=HOMO_SIGN;
                    else if(multiplyOperation==15)state<=GRID_INIT;
                    else begin multiplyOperation<=multiplyOperation+4'd1;state<=HOMO_PRODUCTS;end
                end
                HOMO_SIGN:begin
                    if(determinant==0)begin geometryRejected<=1;state<=DECIDE;end
                    else begin
                        dNorm<=determinant<0?-determinant:determinant;
                        gNorm<=determinant<0?-gNumerator:gNumerator;
                        hNorm<=determinant<0?-hNumerator:hNumerator;
                        state<=HOMO_COEFF;
                    end
                end
                HOMO_COEFF:begin
                    multiplyOperation<=6;state<=HOMO_PRODUCTS;
                end
                GRID_INIT:begin
                    // U=5+10*x and V=4+8*y. Exact row/column recurrence keeps
                    // every homography numerator identical to direct evaluation.
                    // Constant multipliers below reduce to shifts/adds, not DSPs.
                    rowNumeratorX<=ax*48'sd5+bx*48'sd4+cx*48'sd320;
                    rowNumeratorY<=ay*48'sd5+by*48'sd4+cy*48'sd320;
                    rowDenominator<=gNorm*48'sd5+hNorm*48'sd4+dNorm*48'sd320;
                    numeratorX<=ax*48'sd5+bx*48'sd4+cx*48'sd320;
                    numeratorY<=ay*48'sd5+by*48'sd4+cy*48'sd320;
                    denominator<=gNorm*48'sd5+hNorm*48'sd4+dNorm*48'sd320;
                    gridX<=0;gridY<=0;state<=GRID_NUM;
                end
                GRID_NUM:state<=GRID_PREP;
                GRID_PREP:begin
                    // Coordinates are doubled. Add denominator before dividing
                    // by 2*denominator to round to the nearest native pixel.
                    if(denominator<=0||numeratorX+denominator<0||numeratorY+denominator<0)begin mapRejected<=1;state<=DECIDE;end
                    else begin
                        remainderX<=numeratorX+denominator;remainderY<=numeratorY+denominator;
                        divisionDenominator<=denominator<<1;shiftedDenominator<=denominator<<9;
                        divisionBit<=8;quotientX<=0;quotientY<=0;state<=DIVIDE;
                    end
                end
                DIVIDE:begin
                    if(remainderX>=shiftedDenominator)begin remainderX<=remainderX-shiftedDenominator;quotientX[divisionBit]<=1;end
                    if(remainderY>=shiftedDenominator)begin remainderY<=remainderY-shiftedDenominator;quotientY[divisionBit]<=1;end
                    shiftedDenominator<=shiftedDenominator>>1;
                    if(divisionBit==0)state<=MAP_ADDRESS;
                    else divisionBit<=divisionBit-4'd1;
                end
                MAP_ADDRESS:begin
                    if(quotientX>=320||quotientY>=240||remainderX>=divisionDenominator||remainderY>=divisionDenominator)
                        begin mapRejected<=1;state<=DECIDE;end
                    else state<=GRID_WAIT;
                end
                GRID_WAIT:state<=GRID_SAMPLE;
                GRID_SAMPLE:begin
                    if(readWhite)begin
                        if(gridX>=12&&gridX<=19)begin
                            if(gridY>=4&&gridY<=8)strokeProjection[0][gridX-12]<=1;
                            if(gridY>=18&&gridY<=21)strokeProjection[6][gridX-12]<=1;
                            if(gridY>=31&&gridY<=35)strokeProjection[3][gridX-12]<=1;
                        end
                        if(gridY>=10&&gridY<=16)begin
                            if(gridX>=21&&gridX<=24)strokeProjection[1][gridY-10]<=1;
                            if(gridX>=7&&gridX<=10)strokeProjection[5][gridY-10]<=1;
                        end
                        if(gridY>=23&&gridY<=29)begin
                            if(gridX>=21&&gridX<=24)strokeProjection[2][gridY-23]<=1;
                            if(gridX>=7&&gridX<=10)strokeProjection[4][gridY-23]<=1;
                        end
                        if(gridX<=5&&gridY>=1&&gridY<=5)begin
                            anchorCount<=anchorCount+6'd1;anchorColumns[gridX]<=1;anchorRows[gridY-1]<=1;
                        end
                        if(gridX>=13&&gridX<=18)begin
                            if(gridY>=12&&gridY<=15)holeUpperWhite<=holeUpperWhite+6'd1;
                            if(gridY>=24&&gridY<=27)holeLowerWhite<=holeLowerWhite+6'd1;
                        end
                    end
                    if(gridX==31)begin
                        gridX<=0;
                        if(gridY==39)state<=DECIDE;
                        else begin
                            gridY<=gridY+6'd1;
                            rowNumeratorX<=rowNumeratorX+bx*48'sd8;rowNumeratorY<=rowNumeratorY+by*48'sd8;
                            rowDenominator<=rowDenominator+hNorm*48'sd8;
                            numeratorX<=rowNumeratorX+bx*48'sd8;numeratorY<=rowNumeratorY+by*48'sd8;
                            denominator<=rowDenominator+hNorm*48'sd8;state<=GRID_NUM;
                        end
                    end else begin
                        gridX<=gridX+5'd1;numeratorX<=numeratorX+ax*48'sd10;numeratorY<=numeratorY+ay*48'sd10;
                        denominator<=denominator+gNorm*48'sd10;state<=GRID_NUM;
                    end
                end
                DECIDE:begin
                    markers[index]<=decision;if(decision.accepted)acceptedCount<=acceptedCount+5'd1;state<=NEXT;
                end
                NEXT:if(index==15)begin done<=1;state<=IDLE;end
                    else begin index<=index+4'd1;state<=SETUP;end
                default:state<=IDLE;
            endcase
        end
    end
endmodule

// One candidate coefficient product per 12 clocks. operandA is signed 25 bits,
// operandB signed 12 bits; the full exact signed product is 37 bits. The 12-bit
// magnitude handles -2048 without overflowing a signed absolute-value register.
module projectiveSerialMultiply(
    input logic clk,reset,start,
    input logic signed [24:0] operandA,
    input logic signed [11:0] operandB,
    output logic signed [36:0] result,
    output logic done
);
    logic working,negativeB;
    logic [11:0] magnitudeB;
    logic [3:0] bitCount;
    logic signed [36:0] shiftedA,accumulator,nextAccumulator;
    always_comb nextAccumulator=accumulator+(magnitudeB[0]?shiftedA:37'sd0);
    always_ff @(posedge clk)begin
        if(reset)begin
            working<=0;negativeB<=0;magnitudeB<=0;bitCount<=0;
            shiftedA<=0;accumulator<=0;result<=0;done<=0;
        end else begin
            done<=0;
            if(start&&!working)begin
                working<=1;negativeB<=operandB[11];
                magnitudeB<=operandB[11]?-operandB:operandB;
                shiftedA<={{12{operandA[24]}},operandA};accumulator<=0;bitCount<=0;
            end else if(working)begin
                accumulator<=nextAccumulator;shiftedA<=shiftedA<<<1;magnitudeB<=magnitudeB>>1;
                if(bitCount==11)begin
                    result<=negativeB?-nextAccumulator:nextAccumulator;working<=0;done<=1;
                end else bitCount<=bitCount+4'd1;
            end
        end
    end
endmodule
