`timescale 1ns/1ps
// RTL_SIM only. The three semantic predicates are scored independently of
// glyphBanks' two-bit storage encoding; no camera/board acceptance is implied.
// Both banks cover every physical address. During writes the selected read
// bank is always the other bank, so this test does not depend on RAM collision
// behaviour. No reset/initial value is assumed for the production RAM.
module glyphBanks_tb;
    import camera_pkg::*;

    localparam integer pixelCount = 76800;
    logic clk = 1'b0;
    always #5 clk = ~clk;

    logic writeEnable = 1'b0, writeBank = 1'b0;
    logic [16:0] writeAddress = 17'd0;
    logic writeWhite = 1'b0, writeStrongWhite = 1'b0, writeColour = 1'b0;
    logic readBank = 1'b1;
    logic [16:0] readAddress = 17'd0;
    logic readWhite, readStrongWhite, readColour;
    logic [23:0] rgb = 24'd0;
    logic [1:0] colourMask;
    logic [2:0] expectedWrite = 3'd0;

    // Semantic ordering is {white, strongWhite, colour}, not the RAM code.
    logic [2:0] expectedPixels [0:1][0:pixelCount-1];
    bit expectedValid [0:1][0:pixelCount-1];
    logic [2:0] expectedAtEdge, previousExpected;
    bit validAtEdge, previousValid = 1'b0;
    integer predicateChecks = 0, exhaustiveChecks = 0;
    integer readChecks = 0, holdChecks = 0, writeChecks = 0;
    integer weakWhiteCount = 0, strongWhiteCount = 0;
    integer colourCount = 0, backgroundCount = 0;

    glyphBanks dut(.*);
    // Zero value floors maximise the colour set. Any permitted positive floor
    // can only remove colour pixels, so mutual exclusion also holds for it.
    hsvColourGate #(.BLUE_HUE_UPPER(260)) colourGate(
        .rgb(rgb), .redMinimum(8'd0), .blueMinimum(8'd0),
        .colourMask(colourMask)
    );

    function automatic logic [23:0] expandedOracle(input logic [15:0] sample);
        integer red5, green6, blue5;
        begin
            red5 = (sample >> 11) & 31;
            green6 = (sample >> 5) & 63;
            blue5 = sample & 31;
            expandedOracle = {8'((red5 * 8) + (red5 / 4)),
                8'((green6 * 4) + (green6 / 16)),
                8'((blue5 * 8) + (blue5 / 4))};
        end
    endfunction

    function automatic logic [1:0] colourOracle(input logic [23:0] sample);
        real red, green, blue, maximum, minimum, delta, hue, saturation;
        bit redMatch, blueMatch;
        begin
            red = real'(sample[23:16]);
            green = real'(sample[15:8]);
            blue = real'(sample[7:0]);
            maximum = red;
            if (green > maximum) maximum = green;
            if (blue > maximum) maximum = blue;
            minimum = red;
            if (green < minimum) minimum = green;
            if (blue < minimum) minimum = blue;
            delta = maximum - minimum;
            hue = 0.0;
            saturation = 0.0;
            redMatch = 1'b0;
            blueMatch = 1'b0;
            if (delta > 0.0 && maximum > 0.0) begin
                saturation = delta / maximum;
                if (maximum == red) hue = 60.0 * (green - blue) / delta;
                else if (maximum == green) hue = 120.0 + 60.0 * (blue - red) / delta;
                else hue = 240.0 + 60.0 * (red - green) / delta;
                if (hue < 0.0) hue = hue + 360.0;
                // Epsilon accounts only for real arithmetic at exact rational
                // HSV boundaries. It is far below any RGB565 hue step.
                redMatch = saturation >= 0.5 - 1.0e-10 &&
                    (hue >= 336.0 - 1.0e-10 || hue <= 1.0e-10);
                blueMatch = saturation >= 0.5 - 1.0e-10 &&
                    hue >= 200.0 - 1.0e-10 && hue <= 260.0 + 1.0e-10;
            end
            colourOracle = redMatch ? 2'd1 : blueMatch ? 2'd2 : 2'd0;
        end
    endfunction

    function automatic logic [2:0] semanticOracle(input logic [23:0] sample);
        integer red, green, blue, maximum, minimum, weightedSum;
        bit roundedWhite, strongWhite, colour;
        begin
            red = integer'(sample[23:16]);
            green = integer'(sample[15:8]);
            blue = integer'(sample[7:0]);
            maximum = red;
            if (green > maximum) maximum = green;
            if (blue > maximum) maximum = blue;
            minimum = red;
            if (green < minimum) minimum = green;
            if (blue < minimum) minimum = blue;
            weightedSum = red + 2 * green + blue;
            // An independently rounded/floored brightness oracle checks the
            // corresponding direct-sum write predicates below at the boundary.
            strongWhite = (weightedSum / 4 >= 96) && maximum - minimum <= 64;
            roundedWhite = strongWhite || (((weightedSum + 2) / 4 >= 84) &&
                maximum - minimum <= 64 && real'(maximum-minimum)<real'(maximum)/2.0);
            colour = colourOracle(sample) != 2'd0;
            semanticOracle = {roundedWhite, strongWhite, colour};
        end
    endfunction

    task automatic setPixel(input logic [15:0] sample, input bit exhaustive);
        integer red, green, blue, maximum, minimum, weightedSum;
        logic [1:0] expectedColour;
        begin
            rgb = rgb565_to_rgb888(sample);
            if (rgb !== expandedOracle(sample))
                $fatal(1, "RGB565 expansion mismatch sample=%04h", sample);
            red = integer'(rgb[23:16]);
            green = integer'(rgb[15:8]);
            blue = integer'(rgb[7:0]);
            maximum = red;
            if (green > maximum) maximum = green;
            if (blue > maximum) maximum = blue;
            minimum = red;
            if (green < minimum) minimum = green;
            if (blue < minimum) minimum = blue;
            weightedSum = red + 2 * green + blue;
            writeStrongWhite = weightedSum >= 384 && maximum - minimum <= 64;
            writeWhite = writeStrongWhite || (weightedSum >= 334 && maximum - minimum <= 64 &&
                2*(maximum-minimum)<maximum);
            expectedWrite = semanticOracle(rgb);
            expectedColour = colourOracle(rgb);
            #1;
            writeColour = colourMask != 2'd0;
            if (colourMask !== expectedColour ||
                {writeWhite, writeStrongWhite, writeColour} !== expectedWrite)
                $fatal(1, "Pixel oracle mismatch sample=%04h RGB=%06h got=%03b expected=%03b",
                    sample, rgb, {writeWhite, writeStrongWhite, writeColour}, expectedWrite);
            if (writeWhite && writeColour)
                $fatal(1, "Rounded white overlaps raw HSV colour sample=%04h RGB=%06h", sample, rgb);
            if (writeStrongWhite && !writeWhite)
                $fatal(1, "Strong white is not a subset sample=%04h RGB=%06h", sample, rgb);
            predicateChecks++;
            if (exhaustive) begin
                exhaustiveChecks++;
                if (writeStrongWhite) strongWhiteCount++;
                else if (writeWhite) weakWhiteCount++;
                else if (writeColour) colourCount++;
                else backgroundCount++;
            end
        end
    endtask

    // Score the address/bank sampled on this edge, then wait for nonblocking
    // RAM outputs. This rejects extra latency, wrong bank selection and any
    // permutation of the three decoded semantic outputs.
    always @(posedge clk) begin
        if (readAddress >= pixelCount)
            $fatal(1, "Out-of-range read address %0d", readAddress);
        validAtEdge = expectedValid[readBank][readAddress];
        expectedAtEdge = expectedPixels[readBank][readAddress];
        if (writeEnable) begin
            if (writeBank == readBank || writeAddress >= pixelCount)
                $fatal(1, "Test attempted a selected-bank collision or invalid write address");
            expectedPixels[writeBank][writeAddress] = expectedWrite;
            expectedValid[writeBank][writeAddress] = 1'b1;
            writeChecks++;
        end
        #1;
        if (validAtEdge) begin
            if ({readWhite, readStrongWhite, readColour} !== expectedAtEdge)
                $fatal(1, "One-cycle read mismatch bank=%0d address=%0d got=%03b expected=%03b",
                    readBank, readAddress, {readWhite, readStrongWhite, readColour}, expectedAtEdge);
            readChecks++;
        end
        previousExpected = expectedAtEdge;
        previousValid = validAtEdge;
    end

    // The stimulus changes both read inputs at negedge. Registered read data
    // must still describe the preceding posedge until the next rising edge.
    always @(negedge clk) begin
        #2;
        if (previousValid) begin
            if ({readWhite, readStrongWhite, readColour} !== previousExpected)
                $fatal(1, "Read outputs changed before the next clock edge");
            holdChecks++;
        end
    end

    initial begin
        for (integer bank = 0; bank < 2; bank++)
            for (integer address = 0; address < pixelCount; address++)
                expectedValid[bank][address] = 1'b0;

        // Every RGB565 value appears once in each bank, at different physical
        // addresses and in opposite data order. Interleaving exercises bank
        // selection while the other bank is actively being written.
        for (integer pixel = 0; pixel < 65536; pixel++) begin
            @(negedge clk);
            writeEnable = 1'b1; writeBank = 1'b0; writeAddress = 17'(pixel);
            readBank = 1'b1; readAddress = 17'(pixelCount - 1 - (pixel == 0 ? 0 : pixel - 1));
            setPixel(16'(pixel), 1'b1);
            @(negedge clk);
            writeEnable = 1'b1; writeBank = 1'b1; writeAddress = 17'(pixelCount - 1 - pixel);
            readBank = 1'b0; readAddress = 17'(pixel);
            setPixel(16'(65535 - pixel), 1'b1);
        end

        // Fill the remaining 11,264 addresses per bank, including 0/76,799
        // boundaries that differ from the 65,536-value colour-domain size.
        for (integer pixel = 65536; pixel < pixelCount; pixel++) begin
            @(negedge clk);
            writeBank = 1'b0; writeAddress = 17'(pixel);
            readBank = 1'b1; readAddress = 17'(pixelCount - pixel);
            setPixel(16'(pixel * 109 + 37), 1'b0);
            @(negedge clk);
            writeBank = 1'b1; writeAddress = 17'(pixelCount - 1 - pixel);
            readBank = 1'b0; readAddress = 17'(pixel);
            setPixel(16'((~pixel) * 251 + 123), 1'b0);
        end

        // Disable writes, then deliberately vary every write input while
        // reading all addresses in both directions. A missing write enable
        // would corrupt the independent scoreboards and fail a later read.
        for (integer pass = 0; pass < 2; pass++) begin
            for (integer address = 0; address < pixelCount; address++) begin
                for (integer bank = 0; bank < 2; bank++) begin
                    @(negedge clk);
                    writeEnable = 1'b0;
                    readBank = 1'(bank);
                    readAddress = 17'(pass == 0 ? address : pixelCount - 1 - address);
                    writeBank = !readBank;
                    writeAddress = readAddress;
                    // Legal but deliberately changing codes cover all four
                    // storage classes without involving a collision contract.
                    case ((address + bank + pass) % 4)
                        0: begin writeWhite = 0; writeStrongWhite = 0; writeColour = 0; end
                        1: begin writeWhite = 0; writeStrongWhite = 0; writeColour = 1; end
                        2: begin writeWhite = 1; writeStrongWhite = 0; writeColour = 0; end
                        3: begin writeWhite = 1; writeStrongWhite = 1; writeColour = 0; end
                    endcase
                end
            end
        end
        @(negedge clk);
        writeEnable = 1'b0;
        repeat (4) @(negedge clk);
        if (exhaustiveChecks != 131072 || writeChecks != 153600 ||
            weakWhiteCount == 0 || strongWhiteCount == 0 || colourCount == 0 || backgroundCount == 0)
            $fatal(1, "Coverage incomplete exhaustive=%0d writes=%0d weak/strong/colour/background=%0d/%0d/%0d/%0d",
                exhaustiveChecks, writeChecks, weakWhiteCount, strongWhiteCount, colourCount, backgroundCount);
        $display("PASS glyphBanks_tb RGB565=65536 banks=2 exhaustiveChecks=%0d predicateChecks=%0d writes=%0d reads=%0d heldOutputs=%0d weakWhite=%0d strongWhite=%0d colour=%0d background=%0d",
            exhaustiveChecks, predicateChecks, writeChecks, readChecks, holdChecks,
            weakWhiteCount, strongWhiteCount, colourCount, backgroundCount);
        $finish;
    end

    initial begin
        #6000000;
        $fatal(1, "glyphBanks exhaustive memory regression timed out");
    end
endmodule
