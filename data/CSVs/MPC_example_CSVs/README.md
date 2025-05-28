### MPC example using CSV files.

At present, optihood only provides options for Model Predictive Control (MPC) using a full scenario file.

### Example description
- single building
- only space heating (SH) with SH storage
- HP connected to grid and battery 
- PV
- weather and demand profiles

### Missing things
- Are links needed? (only one building) NO!
  - If not, can we leave out the csv file? <- to be implemented
- Stratified storage or normal storage? stratified!
  - Can we leave out one of the csv files? <- remove storage.csv
- Leave out capacity_DHW in transformers.csv?
- 
