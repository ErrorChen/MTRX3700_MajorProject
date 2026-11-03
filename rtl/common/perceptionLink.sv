// Optional SystemVerilog interface for team integration; flat ports use the same types.
interface perceptionLink(input logic CLOCK_50, input logic reset);
    import perception_pkg::*;
    logic [31:0] timeUs;
    logic interactionEnable, interactionPermit;
    targetRequest_t targetRequest;
    logic targetRequestValid, targetRequestReady;
    targetReport_t targetReport;
    logic targetReportValid, targetReportReady;
    queryResult_t queryResult;
    logic queryResultValid, queryResultReady;
    userEvent_t userEvent;
    logic userEventValid, userEventReady;
    perceptionStatus_t status;
    modport perception(input CLOCK_50, reset, timeUs, interactionEnable, interactionPermit,
        targetRequest, targetRequestValid, targetReportReady, queryResultReady, userEventReady,
        output targetRequestReady, targetReport, targetReportValid, queryResult, queryResultValid,
        userEvent, userEventValid, status);
    modport controller(input CLOCK_50, reset, timeUs, targetRequestReady,
        targetReport, targetReportValid, queryResult, queryResultValid, userEvent, userEventValid, status,
        output interactionEnable, interactionPermit, targetRequest, targetRequestValid,
        targetReportReady, queryResultReady, userEventReady);
    modport monitor(input CLOCK_50, reset, timeUs, interactionEnable, interactionPermit,
        targetRequest, targetRequestValid, targetRequestReady, targetReport, targetReportValid,
        targetReportReady, queryResult, queryResultValid, queryResultReady,
        userEvent, userEventValid, userEventReady, status);
endinterface
