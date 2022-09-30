# Data exchange with Hantek DSO 2000 series

Here is an accumulation of scripts that allow to get data from a Hantek DSO 2D15 (and others of this series, I hope); pushing data (ie. configuration and wave generator waveforms) is also on-topic.

## Current status

CH1 and/or CH2 data get fetched, and written in the JSON along with a bit of metadata (like sampling rate).

See [JSON output](doc/json.md) and [CSV/TSV output](doc/csv.md).

```sh
dso-via-scpi my-waveform.csv
dso-via-scpi my-waveform.json
```



## Syntax

```sh
dso-via-scpi [save [waveform]] [-]        # writes TSV to STDOUT
dso-via-scpi [save [waveform]] {filename} # writes TSV, CSV, JSON to file

dso-via-scpi [save] config [-]            # writes text configuration to STDOUT
dso-via-scpi [save] config {filename}     # writes text configuration to file
dso-via-scpi get config {item}            # dump configuration 'item' to STDOUT

dso-via-scpi list                         # lists devices

dso-via-scpi load config [-]              # load text configuration from STDIN
dso-via-scpi load config {filename}       # load text configuration from file

dso-via-scpi load wavegen arb[1-4]        # load waveform for generator 1-4 from STDIN or file
dso-via-scpi save wavegen arb[1-4]        # save waveform generator 1-4 to STDOUT or file

dso-via-scpi example wavegen              # example generator waveform output to STDOUT or file
dso-via-scpi example ggplot2              # example R file using ggplot2 to nicely format TSV data 

dso-via-scpi display gnuplot              # continuous display of waveform via X11 gnuplot
dso-via-scpi display ggplot2              # continuous display of waveform via X11 R and ggplot2
dso-via-scpi display text                 # continuous display of waveform via terminal
```

## Flags (NIY)

- `-v` Verbose Mode
- `-d` Debugging
- `-l` Keep the keyboard locked during continuous display
- `-T` set timeout for USB communication

Would we want samples instead of voltage output??


## TODO

Speedups? Fetching 2 Channels with 4M points each takes ~5mins... and the data seems broken. (Some of the samples when taken with a depth of 400K as well, but most look okay)

40K is ~5secs (okay), 400K about 30 secs (already a bit too long)... no idea whether that can be sped up.
