# ROADMAP.md

> **Current Milestone**: v1.0 complete
> **Next Milestone**: v2.0 - TBD

## Must-Haves (v1.0)
- [x] Python 3.12 Environment setup with Database.
- [x] Parse Flex Query XML correctly.
- [x] Validated data correctly persistent in SQLite.
- [x] Tax compliant FIFO engine for accurately matching lots based on settlement dates.
- [x] Tax categorization engine for mapping to "Anlage KAP".
- [x] Tax Consultant Excel Report Export.
- [x] Local Streamlit UI for the end-user.
- [x] Currency Gains (§ 23 EStG) compliance.

## Milestone v1.0 (Archived)
All phases 0-14 completed and verified. See `.gsd/milestones/v1.0-SUMMARY.md` for details.

## Next Milestone: v1.1 (Planning)
> **Goal**: UI Enhancements & Ingestion Robustness
- [ ] Account ID and Tax Year dynamic dropdowns based on database state.
- [ ] Unknown entity info-messages with location during XML ingestion.
- [ ] Streamlit UI configuration (remove menu/deploy button).
- [ ] Raw database browser tab for data verification.

### Phase 15: XML Ingestion Error Reporting
**Status**: ✅ Complete
**Objective**: Detect unknown entities/models during Flex Query XML parsing and return formatted info-messages with the entity type and file location.

### Phase 16: Streamlit UI Configuration & DB Browser
**Status**: ⬜ Not Started
**Objective**: Remove the Streamlit top-right menu and "Deploy" button. Add a new tab/section to browse raw SQLite database tables.

### Phase 17: Dynamic Account & Tax Year Dropdowns
**Status**: ⬜ Not Started
**Objective**: Modify the "Anlage KAP Report" page to fetch distinct Account IDs from the database for the dropdown, and cascade the "Tax Year" dropdown based on the available data for the selected Account ID.

### Phase 18: Buy-Date Reporting for Gains/Losses
**Status**: ⬜ Not Started
**Objective**: Update the final tax report generation to not only show the sell date for stock and currency gains/losses, but also include the original buy-date of the underlying position.

### Phase 19: Missing Cost-Basis Reporting & Prompts
**Status**: ⬜ Not Started
**Objective**: Enhance report generation to detect sell-trades lacking corresponding buy-trades. Display a list of these missing data points to the user and prompt for confirmation on whether to proceed with generating the report.

## Future Milestone: v2.0 (Planned)
- [ ] Support for multiple broker imports (Trade Republic, Scalable Capital).
- [ ] Advanced corporate action support (Spinoffs, Mergers).
- [ ] Portfolio analytics and dividend forecasting.
