# JSON example

```
src/dso-via-scpi.py save waveform foobar.json
```

```json
{                                                                                                                                                                                             
  "trigger": false,                                                                                                                                                                           
  "running": false,                                                                                                                                                                           
  "channels": [                                                                                                                                                                               
    {
      "channel": 1,                                                                                             
      "enable": true,
+---4002 lines: "voltage":·····································································································································································
+---4002 lines: "samples":·····································································································································································
      "offset": 4,                                                                                                   
      "probe": 10,                                                                                                   
      "scale": 2                                                                                                     
    },                                                                                                               
    {                                                                                                                  
      "channel": 2,
      "enable": true,
+---4002 lines: "voltage":·····································································································································································
+---4002 lines: "samples":·····································································································································································
      "offset": -3,                                                                                                 
      "probe": 10,                                                                                                  
      "scale": 1                                                                                                    
    },                                                                                                               
    {                                                                                                                  
      "channel": 3,
      "enable": false,
      "voltage": 1                                                                                                   
    },                                                                                                               
    {                                                                                                                
      "channel": 4,                                                                                                  
      "enable": false,                                                                                               
      "voltage": 1                                                                                                   
    }                                                                                                                   
  ],                                                                                                                    
  "sampling_rate": 25000,                                                                                               
  "sampling_multiple": 1,                                                                                               
  "trigger_time": 0,                                                                                                    
  "acq_start?": 10                                                                                                      
}
```


## Pure sample bytes

![Figure 1](doc/input-bytes.png)

## Actual voltages

![Figure 2](doc/voltages.png)


vim: set ft=markdown :

