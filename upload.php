<?php

// Put code in html form
//<form action="upload.php" method="post" enctype="multipart/form-data">
//<label for="attachment">Select file to upload:</label>
//<input type ="file" name="attachment" id="attachment" accept=".pdf,.png,.jpg,.jpeg,.docx,.doc,.xls,.xlsx,.csv" required>

$attachment = basename($_FILES["attachment"]["name"]);
$target_dir = "";
$target_file = $target_dir . $attachment;

// $imageFileType = strtolower(pathinfo($target_file,PATHINFO_EXTENSION));
// use mime_content_type to get the file type before uploading
$imageFileType = mime_content_type($_FILES["attachment"]["tmp_name"]);

// Check if image file is an actual image or fake image
// $allowed = array('pdf', 'png', 'jpg', 'jpeg');
$allowed = array('image/png', 'image/jpg', 'image/jpeg', 'application/pdf');
//echo $imageFileType . "<br>2<br>";
if (filesize($_FILES["attachment"]["tmp_name"]) > 26214400 OR !in_array($imageFileType, $allowed)) {
    $check = false;
} else {
    $check = true;
}

//echo "Check: " . $check . "<br><br>";

// FILE UPLOAD
// Generate a unique reference for the file
$ref = uniqid('invoice_', true);

// Check if $uploadOk is set to 0 by an error
if (!$check) {
    //echo "Sorry, your file was not uploaded.";
    // if everything is ok, try to upload file
} else {
    $uploaded_file = $target_dir . $ref . "." . pathinfo($attachment, PATHINFO_EXTENSION);
    if (move_uploaded_file($_FILES["attachment"]["tmp_name"], $uploaded_file)) {
        // echo "The file ". basename($_FILES["attachment"]["name"]). " has been uploaded.\n";
        $file_path = escapeshellarg($uploaded_file);
        $command = "chatbot/bin/python3 comboAI.py $file_path";
        $output = shell_exec($command);
        
        // if ($output === null) {
        //     echo "Error executing Python script or no output received.";
        // } else {
        //     echo nl2br(htmlspecialchars($output)); // Display the output, converting newlines to <br>
        // };
        
    } else {
        echo "Sorry, there was an error uploading your file.\n";
    }
    
    // decode the output from the Python script
    $output = json_decode($output, true);
    // print_r($output); // Print the output array for debugging
    
    // delete the uploaded file after processing
    if (file_exists($uploaded_file)) {
        unlink($uploaded_file);
        //      echo "File deleted successfully.\n";
        //  } else {
        //      echo "File does not exist.\n";
    }
}

?>

<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.7/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-LN+7fdVzj6u52u30Kp6M/trliBMCMKTyK833zpbD+pXdCLuTusPj697FH4R/5mcr" crossorigin="anonymous">
<title>Invoice Data</title>

<style>
h1 {
    margin-bottom: 30px;
}
button {
    margin-top: 20px;
}
</style>
</head>
<body style="margin: 0;
            height: 100vh;
            background-image: url('form-background.jpg');
            background-repeat: no-repeat; 
            background-size: cover; 
            background-position: center;
            display: flex;
            justify-content: center;
            align-items: center;">
<div class="container" style=" width:600px;
                                padding: 20px;
                                background: transparent;
                                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                                text-align: center;">
<h1 style="text-align: center; ">Invoice Data:</h1>
<ul class="list-group">
<?php
if (is_array($output) && !empty($output)) {
    foreach ($output as $key => $value) {
        echo "<li class='list-group-item'><strong>" . htmlspecialchars($key) . ":</strong> " . htmlspecialchars($value) . "</li>";
    }
} else {
    echo "<li class='list-group-item'>No data found.</li>";
}
?>
</ul>
</div>    
</body>
</html>
