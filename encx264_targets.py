
x264_path = 'x264.exe'
common_params = "--threads auto --thread-input {tc} --sar {sar} "+ \
                "--ref {ref} --aq-strength 1.5 "+ \
                "--weightb --mixed-refs --no-fast-pskip "+ \
                "--deblock 1:1 "
                
common_params_pass1 = '--pass 1 --slow-firstpass --stats "{statsFile}" ' + \
                      '--direct auto --trellis 0 --no-8x8dct  --me hex ' + \
                      '--subme 6 --partitions none --b-adapt 2 --output NUL'
                      
common_params_pass2 = '--pass 2 --stats "{statsFile}" --ssim  --direct auto '+ \
                      '--merange 64 ' + \
                      '--me umh --subme 10 --trellis 2 --output "{outFile}"'



encode_targets = {
    "mkv_720p" : {
        "default_sar": "1:1",
        "default_ref": 7,
        "bitrate_ratio": 1.0,
        "common": "--profile high --level 4.1 --bframes 7 " + \
                  "--vbv-bufsize 50000 --vbv-maxrate 50000",
        'pass1': '--crf {crf}',
        "pass2": '--bitrate {bitrate} --partitions "p8x8,b8x8,i4x4,i8x8"',
    },

    "mkv_720p_nopsy" : {
        "default_sar": "1:1",
        "default_ref": 7,
        "common": "--profile high --level 4.1 --bframes 7 --no-psy " + \
                  "--vbv-bufsize 50000 --vbv-maxrate 50000 --psy-rd 0:0",
        'pass1': '--crf {crf}',
        "pass2": '--bitrate {bitrate} --partitions "p8x8,b8x8,i4x4,i8x8"',
    },

    "mkv_1080p" : {
        "default_sar": "1:1",
        "default_ref": 3,
        "common": "--profile high --level 4.1 --bframes 7 " + \
                  "--vbv-bufsize 50000 --vbv-maxrate 50000",
        'pass1': '--crf {crf}',
        "pass2": '--bitrate {bitrate} --partitions "p8x8,b8x8,i4x4,i8x8"',
    },
    "mkv_sd" : {
        "default_sar": "1:1",
        "default_ref": 10,
        "common": " --bframes 10",
        "pass1": '--crf {crf}',
        "pass2": '--bitrate {bitrate} --partitions "p8x8,b8x8,i4x4,i8x8"',
    },
    "sd_dxva" : {
        "default_sar": "1:1",
        "default_ref": 8,
        "common": " --bframes 8  --vbv-bufsize 14000 --vbv-maxrate 14000" + \
                  " --level 3.1 ",
        "pass1": '--crf {crf}',
        "pass2": '--bitrate {bitrate} --partitions "p8x8,b8x8,i4x4,i8x8"',
    },
    "psp" : {
        "default_ref": 3,
        "common": "--profile main --level 3 --bframes 3 --vbv-bufsize 10000 "+ \
                  "--vbv-maxrate 10000  --weightp 0 --b-pyramid none",
        "pass1": '--bitrate {bitrate}',
        "pass2": '--bitrate {bitrate} --partitions "p8x8,b8x8,i4x4"',
    },
    "psp_crf" : {
        "default_ref": 3,
        "common": "--profile main --level 3 --bframes 3 --vbv-bufsize 10000 "+ \
                  "--vbv-maxrate 10000  --weightp 0 --b-pyramid none",
        "pass1": '--crf {crf}',
        "pass2": '--bitrate {bitrate} --partitions "p8x8,b8x8,i4x4"',
    },
}
