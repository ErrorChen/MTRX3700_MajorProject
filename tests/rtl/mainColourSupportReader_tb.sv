`timescale 1ns/1ps
module mainColourSupportReader_tb;
    logic clk=0;always #10 clk=~clk;
    logic reset=1,start=0,readColour,busy,done,geometryValid,overflow;
    logic [8:0] ownerXMin=0,ownerXMax=0,supportX[0:15];
    logic [7:0] ownerYMin=0,ownerYMax=0,supportY[0:15];
    logic [16:0] readAddress,foregroundCount,componentCount;
    logic [3:0] allocationPeak;
    logic colourBank[0:76799],visited[0:76799];
    integer queue[0:76799],bestX[0:15],bestY[0:15],bestScore[0:15];
    integer partX[0:15],partY[0:15],partScore[0:15];
    integer expectedRaw,expectedComponents,expectedArea,expectedX0,expectedY0,expectedX1,expectedY1;
    bit expectedUnique,expectedValid;
    integer checks=0,casesRun=0,maximumCycles=0,currentCase=0,overflowCases=0,externalCases=0;
    integer guardCases=0,mergeCases=0,retiredManyCases=0;
    string mainVectors,fileName;
    logic [31:0] meta[0:4095*42-1],vectorCount[0:0],recordWords[0:0];
    mainColourSupportReader dut(.*);
    always_ff @(posedge clk)readColour<=colourBank[readAddress];
    always @(posedge clk)begin
        #2;
        if(!reset)for(int slot=0;slot<8;slot++)if(!dut.freeSlots[slot])begin
            if(dut.parents[slot]<1||dut.parents[slot]>8||dut.parents[dut.parents[slot]-1]!=dut.parents[slot])
                $fatal(1,"Main colour alias is not canonical case%0d slot%0d",currentCase,slot);
        end
    end
    task automatic clearImage;
        for(int pixel=0;pixel<76800;pixel++)colourBank[pixel]=0;
    endtask
    task automatic rectangle(input integer x0,y0,x1,y1);
        for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++)colourBank[y*320+x]=1;
    endtask
    function automatic integer score(input integer d,x,y);
        // Independent mathematical integer dot-product oracle. The DUT uses
        // bounded signed11 shift/add arithmetic and synchronous support RAM.
        integer a,b;
        begin
            case(d)
                0:begin a=1;b=0;end 1:begin a=2;b=1;end
                2:begin a=1;b=1;end 3:begin a=1;b=2;end
                4:begin a=0;b=1;end 5:begin a=-1;b=2;end
                6:begin a=-1;b=1;end 7:begin a=-2;b=1;end
                8:begin a=-1;b=0;end 9:begin a=-2;b=-1;end
                10:begin a=-1;b=-1;end 11:begin a=-1;b=-2;end
                12:begin a=0;b=-1;end 13:begin a=1;b=-2;end
                14:begin a=1;b=-1;end default:begin a=2;b=-1;end
            endcase
            return a*x+b*y;
        end
    endfunction
    task automatic referenceBfs(input integer x0,y0,x1,y1);
        integer head,tail,pos,x,y,nextX,nextY,nextPos,area,loX,hiX,loY,hiY,s;
        begin
            expectedRaw=0;expectedComponents=0;expectedArea=0;expectedUnique=0;expectedValid=0;
            expectedX0=0;expectedX1=0;expectedY0=0;expectedY1=0;
            for(int d=0;d<16;d++)begin bestX[d]=0;bestY[d]=0;bestScore[d]=-10000;end
            for(int pixel=0;pixel<76800;pixel++)visited[pixel]=0;
            if(x0<=x1&&y0<=y1&&x1<320&&y1<240)begin
                for(int py=y0;py<=y1;py++)for(int px=x0;px<=x1;px++)begin
                    pos=py*320+px;
                    if(colourBank[pos])expectedRaw++;
                    if(colourBank[pos]&&!visited[pos])begin
                        head=0;tail=1;queue[0]=pos;visited[pos]=1;area=0;
                        loX=px;hiX=px;loY=py;hiY=py;
                        for(int d=0;d<16;d++)begin partScore[d]=-10000;partX[d]=0;partY[d]=0;end
                        while(head<tail)begin
                            pos=queue[head];head++;x=pos%320;y=pos/320;area++;
                            if(x<loX)loX=x;if(x>hiX)hiX=x;if(y<loY)loY=y;if(y>hiY)hiY=y;
                            for(int d=0;d<16;d++)begin
                                s=score(d,x,y);
                                if(s>partScore[d]||(s==partScore[d]&&(y<partY[d]||(y==partY[d]&&x<partX[d]))))begin
                                    partScore[d]=s;partX[d]=x;partY[d]=y;
                                end
                            end
                            for(int neighbour=0;neighbour<4;neighbour++)begin
                                nextX=x;nextY=y;
                                case(neighbour)0:nextX=x-1;1:nextX=x+1;2:nextY=y-1;3:nextY=y+1;endcase
                                if(nextX>=x0&&nextX<=x1&&nextY>=y0&&nextY<=y1)begin
                                    nextPos=nextY*320+nextX;
                                    if(colourBank[nextPos]&&!visited[nextPos])begin
                                        visited[nextPos]=1;queue[tail]=nextPos;tail++;
                                    end
                                end
                            end
                        end
                        expectedComponents++;
                        if(area>expectedArea)begin
                            expectedArea=area;expectedUnique=1;
                            expectedX0=loX;expectedY0=loY;expectedX1=hiX;expectedY1=hiY;
                            for(int d=0;d<16;d++)begin bestX[d]=partX[d];bestY[d]=partY[d];bestScore[d]=partScore[d];end
                        end else if(area==expectedArea)expectedUnique=0;
                    end
                end
                expectedValid=expectedUnique&&expectedArea>0&&expectedX0==x0&&expectedY0==y0&&expectedX1==x1&&expectedY1==y1;
            end
        end
    endtask
    task automatic runCase(input integer x0,y0,x1,y1,input bit expectedOverflow);
        integer cycles;
        begin
            currentCase=casesRun;referenceBfs(x0,y0,x1,y1);
            @(negedge clk);ownerXMin=9'(x0);ownerYMin=8'(y0);ownerXMax=9'(x1);ownerYMax=8'(y1);start=1;
            @(negedge clk);start=0;
            // Bounds are transaction data: deliberately destroy every input
            // while work is in flight. A second busy start must also be ignored.
            ownerXMin=319;ownerXMax=0;ownerYMin=239;ownerYMax=0;
            cycles=0;
            while(!done&&cycles<4000000)begin
                @(negedge clk);cycles++;start=cycles==5;
            end
            start=0;
            if(!done)$fatal(1,"Main colour timeout case%0d",casesRun);
            if(busy||overflow!==expectedOverflow||geometryValid!==(expectedValid&&!expectedOverflow))
                $fatal(1,"Main colour flags case%0d got busy%0d valid%0d overflow%0d expected valid%0d overflow%0d",
                    casesRun,busy,geometryValid,overflow,expectedValid&&!expectedOverflow,expectedOverflow);
            checks+=3;
            if(geometryValid)begin
                if(foregroundCount!=expectedRaw||dut.winnerArea!=expectedArea)
                    $fatal(1,"Main colour counts case%0d raw%0d/%0d area%0d/%0d",casesRun,foregroundCount,expectedRaw,dut.winnerArea,expectedArea);
                checks+=2;
                for(int d=0;d<16;d++)begin
                    if(supportX[d]!=bestX[d]||supportY[d]!=bestY[d])
                        $fatal(1,"Main colour support case%0d direction%0d got%0d,%0d expected%0d,%0d",
                            casesRun,d,supportX[d],supportY[d],bestX[d],bestY[d]);
                    checks++;
                end
            end else begin
                if(foregroundCount!=0)$fatal(1,"Rejected geometry leaks foreground count");
                for(int d=0;d<16;d++)if(supportX[d]!=0||supportY[d]!=0)$fatal(1,"Rejected geometry leaks support coordinates");
                checks+=17;
            end
            if(!expectedOverflow)begin
                if(componentCount!=expectedComponents)$fatal(1,"Main colour component count case%0d got%0d expected%0d",casesRun,componentCount,expectedComponents);
                if(allocationPeak>8)$fatal(1,"Unexpected successful capacity peak");
                checks+=2;
            end else begin
                if(allocationPeak!=9)$fatal(1,"Overflow must report attempted ninth handle");
                overflowCases++;checks++;
            end
            casesRun++;if(cycles>maximumCycles)maximumCycles=cycles;
            @(negedge clk);if(done)$fatal(1,"Main colour done must pulse exactly once");
            checks++;
        end
    endtask
    task automatic builtInCases;
        integer randomState;
        begin
            clearImage();runCase(10,20,25,35,0);
            rectangle(10,20,25,35);runCase(10,20,25,35,0);
            clearImage();rectangle(319,239,319,239);runCase(319,239,319,239,0);
            clearImage();rectangle(296,216,319,239);runCase(296,216,319,239,0);
            // Eight live aliases merge on the last row. This exercises supports
            // from the merged-away roots, not just the surviving root's pixels.
            clearImage();for(int i=0;i<8;i++)rectangle(20+4*i,20,20+4*i,39);
            rectangle(20,40,48,40);runCase(20,20,48,40,0);mergeCases++;
            if(allocationPeak!=8||componentCount!=1)$fatal(1,"Eight-root merge coverage missing");
            // Ninth simultaneous seed must reject, never wrap to label0.
            clearImage();for(int i=0;i<9;i++)rectangle(20+3*i,20,20+3*i,30);
            runCase(20,20,44,30,1);
            // The two small ties retire first; a larger enclosing component
            // retires last and restores uniqueness. Its bbox touches all sides.
            clearImage();rectangle(40,40,79,40);rectangle(40,40,40,79);
            rectangle(79,40,79,79);rectangle(40,79,79,79);
            rectangle(48,48,49,49);rectangle(58,48,59,49);runCase(40,40,79,79,0);
            if(!geometryValid||componentCount!=3)$fatal(1,"Retired tie then larger winner coverage missing");
            clearImage();rectangle(20,20,29,29);rectangle(35,20,44,29);runCase(20,20,44,29,0);
            if(geometryValid||dut.winnerUnique)$fatal(1,"Equal largest components must reject");
            // Main bbox must equal the caller's bbox on every side. Small
            // unrelated islands cannot expand the published target location.
            for(int side=0;side<4;side++)begin
                clearImage();rectangle(80,80,103,103);
                case(side)
                    0:begin rectangle(70,85,72,88);runCase(70,80,103,103,0);end
                    1:begin rectangle(85,70,88,72);runCase(80,70,103,103,0);end
                    2:begin rectangle(110,85,112,88);runCase(80,80,112,103,0);end
                    3:begin rectangle(85,110,88,112);runCase(80,80,103,112,0);end
                endcase
                if(geometryValid)$fatal(1,"Mixed bbox side%0d accepted",side);guardCases++;
            end
            // More than16 lifetime components, but at most seven active labels:
            // completed small regions must not consume a finite result pool.
            clearImage();rectangle(100,40,150,40);rectangle(100,40,100,100);
            rectangle(150,40,150,100);rectangle(100,100,150,100);
            for(int y=44;y<98;y+=4)for(int x=106;x<148;x+=8)rectangle(x,y,x,y);
            runCase(100,40,150,100,0);
            if(componentCount<=16||!geometryValid)$fatal(1,"Streaming largest retirement coverage missing");retiredManyCases++;
            // A staggered, interleaved merge graph redirects pre-existing
            // aliases repeatedly before they are reclaimed at row sealing.
            clearImage();
            for(int i=0;i<8;i++)rectangle(60+4*(7-i),40+i,60+4*(7-i),48);
            rectangle(60,48,88,48);rectangle(60,49,60,52);runCase(60,40,88,52,0);mergeCases++;
            // Exhaust every3x3 topology with independent BFS, including
            // diagonal-only contact, ties, holes and first/last-row retirement.
            for(int pattern=0;pattern<512;pattern++)begin
                clearImage();for(int bitIndex=0;bitIndex<9;bitIndex++)
                    colourBank[(120+bitIndex/3)*320+160+bitIndex%3]=(pattern&(1<<bitIndex))!=0;
                runCase(160,120,162,122,0);
            end
            // Deterministic porous large regions exercise tie ordering and
            // score signs at a size different from the exhaustive topology.
            randomState=32'h13579bdf;
            for(int test=0;test<8;test++)begin
                clearImage();rectangle(180,150,203,173);
                for(int y=152;y<172;y+=2)for(int x=182;x<202;x+=2)begin
                    randomState=(randomState<<1)^((randomState<0)?32'h04c11db7:0);
                    if(randomState&1)colourBank[y*320+x]=0;
                end
                runCase(180,150,203,173,0);
            end
            clearImage();runCase(100,20,99,30,0);runCase(0,0,320,20,0);runCase(0,0,20,240,0);
            // Reset while synchronous support updates are in flight cancels
            // the complete operation. RAM is not reset; the next transaction
            // must reinitialise every used support/line entry by ownership.
            clearImage();rectangle(0,0,31,31);
            @(negedge clk);ownerXMin=0;ownerYMin=0;ownerXMax=31;ownerYMax=31;start=1;
            @(negedge clk);start=0;repeat(40)@(negedge clk);reset=1;
            @(negedge clk);if(busy||done||geometryValid||foregroundCount)$fatal(1,"Main colour reset cancellation failed");
            reset=0;runCase(0,0,31,31,0);
        end
    endtask
    task automatic externalVectors;
        integer offset;
        begin
            if($value$plusargs("MAIN_VECTORS=%s",mainVectors))begin
                $readmemh({mainVectors,"/main_colour_count.hex"},vectorCount);
                $readmemh({mainVectors,"/main_colour_record_words.hex"},recordWords);
                if(recordWords[0]!=42||vectorCount[0]>4095)$fatal(1,"Unsupported main-colour fixture schema");
                $readmemh({mainVectors,"/main_colour_meta.hex"},meta,0,vectorCount[0]*42-1);
                for(int n=0;n<vectorCount[0];n++)begin
                    fileName=$sformatf("%s/main_colour_%0d.hex",mainVectors,n);$readmemh(fileName,colourBank);
                    offset=n*42;
                    runCase(meta[offset],meta[offset+1],meta[offset+2],meta[offset+3],meta[offset+5]!=0);
                    if(geometryValid!==meta[offset+4][0]||foregroundCount!=meta[offset+6]||allocationPeak!=meta[offset+8])
                        $fatal(1,"Main-colour exported metadata mismatch vector%0d",n);
                    if(geometryValid&&dut.winnerArea!=meta[offset+7])$fatal(1,"Main-colour exported area mismatch vector%0d",n);
                    if(meta[offset+9]!=32'hffffffff&&componentCount!=meta[offset+9])$fatal(1,"Main-colour exported components mismatch vector%0d",n);
                    for(int d=0;d<16;d++)if(supportX[d]!=meta[offset+10+2*d]||supportY[d]!=meta[offset+11+2*d])
                        $fatal(1,"Main-colour exported support mismatch vector%0d direction%0d",n,d);
                    checks+=20;externalCases++;
                end
            end
        end
    endtask
    initial begin
        clearImage();repeat(3)@(negedge clk);reset=0;
        builtInCases();externalVectors();
        if(guardCases!=4||mergeCases!=2||overflowCases<1||retiredManyCases!=1)$fatal(1,"Main colour branch coverage missing");
        $display("PASS mainColourSupportReader_tb cases=%0d checks=%0d external=%0d maxCycles=%0d overflow=%0d",casesRun,checks,externalCases,maximumCycles,overflowCases);
        $finish;
    end
endmodule
