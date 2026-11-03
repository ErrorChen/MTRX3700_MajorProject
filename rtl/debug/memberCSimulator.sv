// Non-motor C reference consumer. Debug commands are interface stimuli, never
// microphone recognition. Every field and age calculation stays in CLOCK_50.
module memberCSimulator #(
    parameter logic [31:0] MAX_AGE_US = 32'd150000,
    parameter logic [31:0] EVENT_MAX_AGE_US = 32'd2000000,
    parameter logic [31:0] CYCLE_PERIOD_US = 32'd2000000
) (
    input logic clk, reset,
    input logic [31:0] timeUs,
    input logic commandValid,
    output logic commandReady,
    input perception_pkg::targetOperation_t commandOperation,
    input perception_pkg::markerType_t commandMarkerType,
    input logic [3:0] commandDigit,
    input logic autoCycle, interactionEnable, interactionPermit,
    input perception_pkg::perceptionStatus_t status,
    output perception_pkg::targetRequest_t targetRequest,
    output logic targetRequestValid,
    input logic targetRequestReady,
    input perception_pkg::targetReport_t targetReport,
    input logic targetReportValid,
    output logic targetReportReady,
    input perception_pkg::userEvent_t userEvent,
    input logic userEventValid,
    output logic userEventReady,
    output perception_pkg::targetReport_t cachedReport,
    output logic measurementUsable,
    output perception_pkg::targetRequest_t currentRequest,
    output logic acceptedEventPulse, rejectedEventPulse
);
    import perception_pkg::*;
    logic running, haveMeasurement, haveReportSequence, haveEventSequence;
    logic previousEnable, previousPermit, haveCancelCutoff, haveCancelledInteraction;
    logic [15:0] nextRequestTag, lastReportId, lastEventId, cancelledInteraction;
    logic [15:0] previousConfig;
    logic [31:0] cancelCutoffUs, lastCycleUs;
    logic [3:0] nextCycleBay;
    logic requestSlotAvailable, cancellationNow, acceptedProposal;
    logic [31:0] sinceCancelUs, afterCutoffUs, sinceCycleUs;
    logic cancelFenceActive, preCancelProposal;

    always_comb begin
        requestSlotAvailable = !targetRequestValid || targetRequestReady;
        commandReady = running && !reset && requestSlotAvailable;
        targetReportReady = running && !reset;
        // Reserve a request slot before taking an event: accepted speech must
        // produce exactly one independent SELECT, even during request backpressure.
        userEventReady = running && !reset && requestSlotAvailable && !commandValid;
        cancellationNow = (previousEnable && !interactionEnable) ||
                          (previousPermit && !interactionPermit);
        sinceCancelUs = timeUs - cancelCutoffUs;
        afterCutoffUs = userEvent.issuedAtUs - cancelCutoffUs;
        sinceCycleUs = timeUs - lastCycleUs;
        cancelFenceActive = haveCancelCutoff && sinceCancelUs <= EVENT_MAX_AGE_US;
        preCancelProposal = cancelFenceActive && (afterCutoffUs == 0 || afterCutoffUs[31]);
        acceptedProposal = userEvent.eventType == EVENT_SPEECH_BAY_REQUEST &&
            (!haveEventSequence || newerSequence(userEvent.eventId,lastEventId)) &&
            interactionEnable && interactionPermit && !cancellationNow &&
            userEvent.interactionId == status.interactionId &&
            !(haveCancelledInteraction && userEvent.interactionId == cancelledInteraction) &&
            !preCancelProposal && userEvent.configVersion == status.activeCfgVersion &&
            userEvent.reason == REASON_OK && userEvent.quality != 0 &&
            bayEnabled(userEvent.bayId) && freshTime(timeUs,userEvent.issuedAtUs,EVENT_MAX_AGE_US);
        // Re-evaluate age every clock: an absence of new packets never extends a
        // measurement's lifetime. Initial 150 ms is a budget, not measured latency.
        measurementUsable = running && !reset && haveMeasurement &&
            currentRequest.operation == TARGET_SELECT && markerEnabled(currentRequest.markerType,currentRequest.digit) &&
            cachedReport.requestTag == currentRequest.requestTag &&
            cachedReport.markerType == currentRequest.markerType &&
            cachedReport.digit == currentRequest.digit &&
            cachedReport.configVersion == status.activeCfgVersion &&
            cachedReport.targetSelected && cachedReport.frameGood && cachedReport.observed &&
            cachedReport.locked && !cachedReport.ambiguous &&
            status.perceptionReady && !status.interactionBusy &&
            freshTime(timeUs,cachedReport.captureStartUs,MAX_AGE_US);
    end

    always_ff @(posedge clk) begin
        if (reset) begin
            running <= 0;
            targetRequest <= '0;
            targetRequestValid <= 0;
            currentRequest <= '0;
            currentRequest.digit <= INVALID_BAY_ID;
            cachedReport <= '0;
            haveMeasurement <= 0;
            haveReportSequence <= 0;
            haveEventSequence <= 0;
            lastReportId <= 0;
            lastEventId <= 0;
            nextRequestTag <= 1;
            previousConfig <= 0;
            previousEnable <= 0;
            previousPermit <= 0;
            haveCancelCutoff <= 0;
            haveCancelledInteraction <= 0;
            cancelCutoffUs <= 0;
            cancelledInteraction <= 0;
            lastCycleUs <= 0;
            nextCycleBay <= 1;
            acceptedEventPulse <= 0;
            rejectedEventPulse <= 0;
        end else begin
            running <= 1;
            previousEnable <= interactionEnable;
            previousPermit <= interactionPermit;
            previousConfig <= status.activeCfgVersion;
            acceptedEventPulse <= 0;
            rejectedEventPulse <= 0;
            if (haveCancelCutoff && sinceCancelUs > EVENT_MAX_AGE_US)
                haveCancelCutoff <= 0;
            // Current-interaction equality now rejects the old cancelled session;
            // release its tombstone before a later legal 16-bit identifier wrap.
            if (haveCancelledInteraction && status.interactionId != cancelledInteraction)
                haveCancelledInteraction <= 0;
            if (cancellationNow) begin
                haveCancelCutoff <= 1;
                cancelCutoffUs <= timeUs;
                if (status.interactionBusy) begin
                    haveCancelledInteraction <= 1;
                    cancelledInteraction <= status.interactionId;
                end
            end
            if (targetReportValid && targetReportReady &&
                targetReport.requestTag == currentRequest.requestTag &&
                targetReport.configVersion == status.activeCfgVersion &&
                (!markerEnabled(currentRequest.markerType,currentRequest.digit) ||
                 (targetReport.markerType == currentRequest.markerType && targetReport.digit == currentRequest.digit)) &&
                (!haveReportSequence || newerSequence(targetReport.frameId,lastReportId))) begin
                cachedReport <= targetReport;
                lastReportId <= targetReport.frameId;
                haveReportSequence <= 1;
                haveMeasurement <= targetReport.frameGood && targetReport.observed && targetReport.locked &&
                    !targetReport.ambiguous && targetReport.targetSelected;
            end
            if (previousConfig != status.activeCfgVersion) begin
                haveMeasurement <= 0;
                haveReportSequence <= 0;
            end
            if (targetRequestValid && targetRequestReady) begin
                targetRequestValid <= 0;
                // LIST/GET have their own response stream and tag. Taking a
                // query must not clear or relabel the live tracking cache.
                if (targetRequest.operation == TARGET_SELECT || targetRequest.operation == TARGET_CLEAR) begin
                    currentRequest <= targetRequest;
                    haveMeasurement <= 0;
                    haveReportSequence <= 0;
                end
            end
            if (userEventValid && userEventReady) begin
                if (!haveEventSequence || newerSequence(userEvent.eventId,lastEventId)) begin
                    lastEventId <= userEvent.eventId;
                    haveEventSequence <= 1;
                end
                acceptedEventPulse <= acceptedProposal;
                rejectedEventPulse <= userEvent.eventType == EVENT_SPEECH_BAY_REQUEST && !acceptedProposal;
            end
            // Presented request payload remains immutable while !ready. Debug
            // requests and speech proposals share exactly this same transaction path.
            if (commandValid && commandReady) begin
                targetRequest.operation <= commandOperation;
                targetRequest.requestTag <= nextRequestTag;
                targetRequest.markerType <= commandOperation == TARGET_CLEAR ? MARKER_NONE : commandMarkerType;
                targetRequest.digit <= commandOperation == TARGET_CLEAR ? INVALID_BAY_ID : commandDigit;
                targetRequestValid <= 1;
                nextRequestTag <= nextRequestTag + 16'd1;
            end else if (userEventValid && userEventReady && acceptedProposal) begin
                targetRequest.operation <= TARGET_SELECT;
                targetRequest.requestTag <= nextRequestTag;
                targetRequest.markerType <= MARKER_BAY;
                targetRequest.digit <= userEvent.bayId;
                targetRequestValid <= 1;
                nextRequestTag <= nextRequestTag + 16'd1;
            end else if (running && autoCycle && requestSlotAvailable &&
                         !sinceCycleUs[31] && sinceCycleUs >= CYCLE_PERIOD_US) begin
                targetRequest.operation <= TARGET_SELECT;
                targetRequest.requestTag <= nextRequestTag;
                targetRequest.markerType <= MARKER_BAY;
                targetRequest.digit <= nextCycleBay;
                targetRequestValid <= 1;
                nextRequestTag <= nextRequestTag + 16'd1;
                nextCycleBay <= nextCycleBay == 6 ? 4'd1 : nextCycleBay + 4'd1;
                lastCycleUs <= timeUs;
            end
        end
    end
endmodule
