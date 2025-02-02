import streamlit as st
import face_recognition
from pymongo import MongoClient
from PIL import Image
import io
import pandas as pd

sessionList = ["batch", "branch", "roll_number", "result"]
for i in sessionList:
    if i not in st.session_state:
        st.session_state[i]=None
# --- Authenticator Class ---
class Authenticator:
    def __init__(self, mongo_uri='mongodb://localhost:27017/', db_name='authDB'):
        # MongoDB connection
        self.client = MongoClient(mongo_uri)
        self.db = self.client["StudentsDB"]
        self.studentsCollection = self.db['StudentsCollection']
        self.scheduledDB = self.client["ScheduledExams"]
        self.validationDB=self.client["validationDB"]

    def face_recognition_compare(self, stored_photo, taken_photo):
        try:
            # Get face encodings from both photos
            stored_face_encoding = self.get_face_encoding(stored_photo)
            taken_face_encoding = self.get_face_encoding(taken_photo)

            if stored_face_encoding is not None and taken_face_encoding is not None:
                # Compare the encodings using face_recognition library
                results = face_recognition.compare_faces([stored_face_encoding], taken_face_encoding)
                distance = face_recognition.face_distance([stored_face_encoding], taken_face_encoding)[0]
                similarity = (1 - distance) * 100  # Convert to percentage

                # Threshold can adjust based on needs
                threshold = 60.0
                if similarity >= threshold:
                    return similarity, True
                else:
                    return similarity, False
            else:
                return 0, False
        except Exception as e:
            st.error(f"Error during face recognition: {e}")
            return 0, False

    def get_face_encoding(self, photo):
        try:
            # Load the photo using face_recognition
            image = face_recognition.load_image_file(io.BytesIO(photo))
            face_encodings = face_recognition.face_encodings(image)

            if len(face_encodings) > 0:
                return face_encodings[0]
            return None
        except Exception as e:
            st.error(f"Error loading image for encoding: {e}")
            return None

    def find_student(self, batch, branch, roll_number):
        try:
            # Fetch student document from MongoDB
            found_details = self.studentsCollection.find_one({
                "batch": batch,
                "branch": branch,
                "roll_number": roll_number.upper()
            })

            return found_details
        except Exception as e:
            st.error(f"An error occurred while fetching student details: {e}")
            return None

    def display(self):
        st.set_page_config(page_title="Face Recognition App", layout="wide")

        # Create Tabs
        tabs = st.tabs(["Login", "Check Schedule", "Download Hall Ticket","Check Status"])

        # --- Admin Tab ---
        with tabs[2]:
            st.header("Admin Panel")
            st.write("Admin functionalities go here.")

        # --- Teacher Tab ---
        with tabs[1]:
            col1, col2 = st.columns([1, 2], border=True)
            self.collection = col1.selectbox("select exam", self.scheduledDB.list_collection_names())
            self.collection=self.scheduledDB[self.collection]
            self.date = col1.selectbox("select date", self.collection.distinct("date"))
            subjectsList, time, session = [], [], []
            for doc in self.collection.find({'date': self.date}):
                subjectsList.append(doc['subject'])
                time.append(doc['start-time'])
                session.append(doc['session'])
            data = pd.DataFrame({'subjects': subjectsList, 'time': time, 'session': session})
            col2.subheader("Exams Details Here",divider='blue')
            col2.dataframe(data)
                

        # --- Students Tab ---
        with tabs[0]:
            st.header("Student Verification")

            # Create two columns with ratio 1:2
            col1, col2,col3 = st.columns([1, 2,1],border=True)            # --- Column 1: Display Image ---
            with col1:
                try:
                    st.image('https://media.tenor.com/YJAxfuECQgkAAAAi/curiouspiyuesh-piyueshmodi.gif',use_container_width=True)
                except:
                    st.warning("Image not available.")

            # --- Column 2: Input Fields ---
            with col2:
                st.subheader("Enter Your Details")

                self.batch = st.selectbox("Select Batch", options=self.studentsCollection.distinct("batch"))
                self.branch = st.selectbox("Select Branch", options=self.studentsCollection.distinct("branch"))
                self.roll_number = st.text_input("Enter Roll Number")

                if st.checkbox("Find Student"):
                    if not all([self.batch, self.branch, self.roll_number]):
                        st.error("Please fill in all the details.")
                    else:
                        self.student = self.find_student(self.batch, self.branch, self.roll_number)
                        if self.student:
                            st.success(f"Verification completed: {self.student.get('fullname', 'N/A')}")

                            # Display Stored Photos
                            self.stored_front_photo = Image.open(io.BytesIO(self.student.get("front_photo", b'')))
                            self.stored_left_photo = Image.open(io.BytesIO(self.student.get("left_photo", b'')))
                            self.stored_right_photo = Image.open(io.BytesIO(self.student.get("right_photo", b'')))
                            col3.image(self.stored_front_photo, caption="Front Photo", use_container_width=True)
                            col3.image(self.stored_left_photo, caption="Left Profile Photo", use_container_width=True)
                            col3.image(self.stored_right_photo, caption="Right Profile Photo", use_container_width=True)

                            # Camera Input for Verification
                            st.subheader("Take a Photo for Verification")
                            self.taken_photo = st.camera_input("Take a photo to verify your identity")

                            if self.taken_photo:
                                # Convert taken photo to bytes
                                self.taken_photo_bytes = self.taken_photo.getvalue()
                                self.taken_image = Image.open(io.BytesIO(self.taken_photo_bytes))

                                # Display taken photo
                                st.image(self.taken_image, caption="Taken Photo", use_container_width=True)

                                # Perform Face Recognition using front_photo
                                st.info("Performing face recognition...")
                                self.similarity, self.is_match = self.face_recognition_compare(self.student.get("front_photo", b''), self.taken_photo_bytes)

                                st.write(f"**Similarity:** {self.similarity:.2f}%")
                                if self.similarity >= 50.0:
                                    st.success("Faces matched successfully!")
                                    st.session_state.update({
                                        "branch": self.branch,
                                        "batch": self.batch,
                                        "roll_number": self.roll_number,
                                        "result":self.similarity
                                    })
                                else:
                                    st.error("Faces do not match.")

                        else:
                            st.error("Student not found. Please check your details.")
        with tabs[3]:
            col1, col2 = st.columns([1, 2], border=True)
            collection = col1.selectbox("select exam", self.validationDB.list_collection_names())
            validation_collection=self.validationDB[collection]
            date = col1.selectbox("selct date of conduction", validation_collection.distinct("date"))
            rollNumber = col1.text_input("Roll number")
            if rollNumber and date:
                rollNumber.upper()
                result = validation_collection.find({"hall_ticket_number": rollNumber, "date": date}, {'_id': 0})
                col2.subheader("Your Status In Exams", divider=True)
                subjectList,subjectCredits,subjectTypes,faceStatus,qrStatus,thumbStatus,finalStatus=[],[],[],[],[],[],[]
                for doc in result:
                    subjectList.append(doc["subject"])
                    subjectCredits.append(doc["subject_credits"])
                    subjectTypes.append(doc["subject_types"])
                    faceStatus.append(doc["studentFaceRecognitionStatus"])
                    qrStatus.append(doc["studentQRCodeStatus"])
                    thumbStatus.append(doc["studentThumbStatus"])
                    finalStatus.append(doc["StudentsFinalStatus"])
                dataframe = pd.DataFrame({'subjects': subjectList, 'subjectCredits': subjectCredits,
                'subjectTypes': subjectTypes, 'faceStatus': faceStatus,
                'qrStatus': qrStatus, 'thumb status': thumbStatus, 'finalStatus': finalStatus})
                col2.dataframe(dataframe)


# --- Main Function ---
def main():
    auth = Authenticator()
    auth.display()

if __name__ == "__main__":
    main()
