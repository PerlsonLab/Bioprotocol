from ij import IJ, ImagePlus
from ij.plugin import RGBStackMerge
from ij.gui import GenericDialog
import os
import re

def main():
    # Select main folder
    main_folder = IJ.getDirectory("Select the split images folder")
    if main_folder is None:
        return

    chosen_folder_name = os.path.basename(os.path.normpath(main_folder))

    # Step 3: Extract available channel names from subfolder names
    available_channels = []
    for subfolder_name in os.listdir(main_folder):
        if subfolder_name.startswith("Channel_"):
            parts = subfolder_name.split("_", 2)
            if len(parts) == 3:
                ch_name = parts[2]
                available_channels.append(ch_name)

    # Remove duplicates, preserve order
    available_channels = list(dict.fromkeys(available_channels))

    if not available_channels:
        IJ.showMessage("Error", "No valid 'Channel_x_channelname' subfolders found.")
        return

    # Reverse order for left-to-right display
    available_channels = available_channels[::-1]

    # Open a checkbox dialog for selecting channels (Step 3)
    gd = GenericDialog("Select Channels to Merge")
    for ch_name in available_channels:
        gd.addCheckbox(ch_name, True)
    gd.showDialog()

    if gd.wasCanceled():
        return

    # Collect selected channels
    selected_channels = []
    for i, ch_name in enumerate(available_channels):
        if gd.getNextBoolean():
            selected_channels.append(ch_name)

    if not selected_channels:
        IJ.showMessage("Cancelled", "No channels selected.")
        return

    # Step 3.5: Ask user to choose the order of selected channels (preserving left-to-right order)
    gd_order = GenericDialog("Select Merge Order")
    for i in range(len(selected_channels)):
        gd_order.addChoice("Position {}:".format(i+1), selected_channels, selected_channels[i])
    gd_order.showDialog()
    if gd_order.wasCanceled():
        return

    # Read the chosen order
    ordered_channels = []
    for i in range(len(selected_channels)):
        chosen_ch = gd_order.getNextChoice()
        if chosen_ch in ordered_channels:
            IJ.showMessage("Invalid Selection", "Duplicate channel '{}' in order.".format(chosen_ch))
            return
        ordered_channels.append(chosen_ch)

    # Step 4: Create output folder alongside the selected folder, appending channel names
    parent_dir = os.path.dirname(os.path.normpath(main_folder))
    channel_suffix = "_".join(ordered_channels)
    merged_folder_base = os.path.join(parent_dir, "merged_" + chosen_folder_name + "_" + channel_suffix)
    merged_folder = merged_folder_base
    suffix = 1
    while os.path.exists(merged_folder):
        merged_folder = "{}_{}".format(merged_folder_base, suffix)
        suffix += 1
    os.mkdir(merged_folder)


    # Dictionary to collect images by base name
    image_groups = {}
    for subfolder_name in os.listdir(main_folder):
        subfolder_path = os.path.join(main_folder, subfolder_name)
        if not os.path.isdir(subfolder_path):
            continue

        for filename in os.listdir(subfolder_path):
            if re.search(r"\.(tif|tiff)$", filename, re.IGNORECASE):
                match = re.match(r"^(.*)_(.+)\.(tif|tiff)$", filename, re.IGNORECASE)
                if match:
                    base_name = match.group(1)
                    ch_name = match.group(2)
                    image_path = os.path.join(subfolder_path, filename)
                    if base_name not in image_groups:
                        image_groups[base_name] = []
                    image_groups[base_name].append((ch_name, image_path))

    # Step 5: Merge images for each base name using selected and ordered channels
    missing_report = []
    for base_name, images in image_groups.items():
        available_images = {ch_name: path for (ch_name, path) in images}

        channels_to_merge = []
        missing_channels = []
        for ch in ordered_channels:
            if ch in available_images:
                channels_to_merge.append(ch)
            else:
                missing_channels.append(ch)

        # Skip merging if any selected channels are missing
        if missing_channels:
            missing_report.append("In '{}': Missing channels {}. Merging skipped.".format(
                base_name, ", ".join(missing_channels)))
            continue

        # Open images for merging
        merge_list = []
        for ch in channels_to_merge:
            imp = IJ.openImage(available_images[ch])
            if imp is not None:
                merge_list.append(imp)

        if not merge_list:
            continue

        if len(merge_list) == 1:
            merged_imp = merge_list[0]
        else:
            merged_imp = RGBStackMerge.mergeChannels(merge_list, True)
            if merged_imp is None:
                missing_report.append("In '{}': Merge failed.".format(base_name))
                for imp in merge_list:
                    imp.close()
                continue

        merged_imp.setDisplayMode(IJ.COLOR)
        channel_suffix = "_".join(channels_to_merge)
        save_path = os.path.join(merged_folder, base_name + "_merged_" + channel_suffix + ".tif")
        IJ.saveAs(merged_imp, "Tiff", save_path)

        for imp in merge_list:
            if imp != merged_imp:
                imp.close()
        merged_imp.close()

    final_message = "Images processed and saved in:\n{}\n".format(merged_folder)
    if missing_report:
        final_message += "\nIssues encountered:\n\n" + "\n".join(missing_report)
    else:
        final_message += "\nNo issues encountered."

    IJ.showMessage("Merge Report", final_message)

# Run the script
main()
